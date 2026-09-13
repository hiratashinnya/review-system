#!/usr/bin/env bash
# レートリミット解除後に tmux ペインへ継続メッセージを送出して対話セッションを再開させる watcher。
#
# 呼び出し元: on-rate-limit.sh から setsid で切り離して起動される(WSL 内 + tmux 前提)。
# 引数: $1=tmux ペインID  $2=session_id
#
# 動作:
#   1) ペインのレート制限テキストからリセット時刻を抽出。取り逃したら短間隔で再取得を
#      リトライする(watcher がバナー描画より先に起動する競合対策=当てずっぽうの早撃ち防止)。
#   2) 時刻を取得できたらリセット(+マージン)まで sleep。最後まで取得できず制限バナーだけ
#      観測できた場合は、当てずっぽうに時刻発火せず「バナー消滅(=リセット発生)」まで待つ。
#      バナーを一度も観測できなければ注入しない(誤発火防止)。
#   3) 注入直前に worktree 掃引を1度だけ実行(Issue #502)。ここは「解除済み」かつ「当該ペインが
#      アイドル」を両方観測できた地点であり、異常終了で `running` のまま残った worktree
#      所有台帳 entry を安全に解放できる契機になる。検知経路は二重化せず、この復帰イベントに
#      相乗りさせる(オーナー指示 2026-09-08)。掃引は `timeout` で括り、終わったら
#      pane_guard を取り直してから 4) へ進む(F-502-06)。
#   4) ペインへ継続メッセージ + Enter を送出
#   5) まだ制限中ならバックオフして再送(上限あり)
#
# 設定(すべて環境変数で上書き可):
set -u

PANE="${1:?pane id required}"
SESSION_ID="${2:-}"

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 共有ガード(状態パス・ペイン判定・tmux timeout ラッパ)。on-rate-limit.sh と共有。
# tmux 呼び出しを rl_tmux(timeout ラップ)経由にすることで、tmux ハング時に flock を
# 永久保持して以後の自動再開を殺すのを防ぐ。lib が無ければ機能しないので即中断。
# ※ source 前は RL_STATE_DIR が未定義なので、FATAL ログのパスだけはリテラルで書く。
# shellcheck source=lib-pane-guard.sh
if ! source "${HOOK_DIR}/lib-pane-guard.sh" 2>/dev/null; then
  # 状態ディレクトリを作るのは lib 自身なので、lib 読込失敗時は未作成のことがある。
  # FATAL を痕跡ゼロで握り潰さないよう、ここで best-effort に mkdir してから追記する。
  mkdir -p "${HOME}/.claude/rate-limit-recovery" 2>/dev/null || true
  printf '%s [watcher] FATAL: lib-pane-guard.sh を読み込めません; abort\n' "$(date '+%F %T')" \
    >> "${HOME}/.claude/rate-limit-recovery/watcher.log" 2>/dev/null || true
  exit 0
fi
# 状態パスは共有ライブラリの RL_STATE_DIR に一元化(二重定義の drift 防止)。
STATE_DIR="$RL_STATE_DIR"
LOG="${STATE_DIR}/watcher.log"
# ペイン別ロックのパスは共有 slug ヘルパで生成(on-rate-limit.sh と同一の正規化)。
LOCK="${STATE_DIR}/lock.$(rl_pane_slug "$PANE")"

CONTINUE_MSG_OVERRIDE="${CLAUDE_RL_CONTINUE_MSG:-}"  # 明示指定時はそのまま送出(時刻注記なし)。未指定なら②の自動生成文を使う
RESET_POLL_INTERVAL="${CLAUDE_RL_RESET_POLL_INTERVAL:-15}"   # リセット時刻の再取得ポーリング間隔秒
RESET_POLL_MAX="${CLAUDE_RL_RESET_POLL_MAX:-40}"             # 再取得の最大試行回数(15s×40=10分)
BANNER_POLL_INTERVAL="${CLAUDE_RL_BANNER_POLL_INTERVAL:-30}"  # 時刻不明時: バナー消滅を待つ間隔秒
BANNER_POLL_MAX="${CLAUDE_RL_BANNER_POLL_MAX:-720}"          # 同上限(30s×720=6時間の安全上限)
MARGIN="${CLAUDE_RL_MARGIN:-30}"                     # リセット時刻に足すマージン秒
MAX_ATTEMPTS="${CLAUDE_RL_MAX_ATTEMPTS:-1}"          # 注入試行上限(既定1=単発。>1で早撃ち救済リトライ)
RETRY_BACKOFF="${CLAUDE_RL_RETRY_BACKOFF:-300}"      # 再注入バックオフ基本間隔秒
VERIFY_WAIT="${CLAUDE_RL_VERIFY_WAIT:-20}"           # 注入後に状態を再確認するまでの待機秒
# バナー走査行数。検知(acquire の capture)と解除判定(is_limit_screen)で同じ窓を使う
# ことで「16〜40行目のバナーは検知できるが解除判定では見えない」不一致を無くす(Issue #240 B1)。
BANNER_SCAN_LINES="${CLAUDE_RL_BANNER_SCAN_LINES:-40}"
# 抽出したリセット時刻が「今より過去」だったとき、翌日へロールするか直近リセットとして扱うかの
# 境界秒。リセット直後の数秒(バナーがまだ残る時間帯)に解析すると翌日扱いになり約24時間 sleep する
# 退化を防ぐ(Issue #240 B3)。過去 GRACE 秒以内は「今まさにリセット」とみなし tomorrow へロールしない。
ROLLOVER_GRACE="${CLAUDE_RL_ROLLOVER_GRACE:-900}"
# 注入を許可する前景コマンド(RL_PANE_CMD_RE)は共有ガード lib-pane-guard.sh で定義(CLAUDE_RL_PANE_CMD_RE で上書き可)

# ログ書式は共有ファクトリ rl_log_line に集約(hook と同一書式・Issue #240 C3)。
log() { rl_log_line "$LOG" "[watcher $PANE]" "$*"; }

# --- ペイン状態の判定(入力欄付近の数行だけを見る=スクロールバックの語句で誤爆しない) ---
pane_tail() { rl_tmux capture-pane -p -t "$PANE" 2>/dev/null | tail -n "${1:-4}"; }

# Claude が作業中(=既に再開して動いている)か。中断ヒント等で判定。出たら絶対に注入しない。
# 入力欄フッタ付近(末尾8行)だけを見る=スクロールバックの語句で誤爆しない。
is_working() {
  pane_tail 8 | grep -qiE "to interrupt|interrupt\)|interrupt to|ctrl\+c to (stop|interrupt)"
}

# レート制限バナーがペインに見えるか(情報ログ専用・注入の可否判定には使わない)。
# 注意: リセット後はバナーが消えるため、これを注入の必須条件にすると
#   「バナー無し=再開済み」と誤認して永遠に注入しなくなる(旧バグ・自動再開が機能しない)。
# バナーはフッタ入力欄より上に出るため末尾 BANNER_SCAN_LINES 行を見る。検知側(acquire の
# capture・tail -n "$BANNER_SCAN_LINES")と同じ窓を使い、検知できるが解除判定で見えない
# 不一致を無くす(Issue #240 B1)。
# `resets 3pm` の数字直後型に加え `resets at 3pm` / `resets at Mon` の "at" 付きも拾う(Issue #240 B2)。
LIMIT_BANNER_RE='resets?[[:space:]]+(at[[:space:]]+)?(mon|tue|wed|thu|fri|sat|sun|[0-9])|hit your (session|weekly|usage|5-hour|account) limit|usage limit|/upgrade|upgrade to'
is_limit_screen() {
  pane_tail "$BANNER_SCAN_LINES" | grep -qiE "$LIMIT_BANNER_RE"
}
# 既に capture 済みのテキストに対する制限バナー判定(acquire ループで再 capture を避け、
# saw_banner と時刻抽出を同一スナップショットで評価するため)。
text_has_banner() {
  printf '%s' "$1" | grep -qiE "$LIMIT_BANNER_RE"
}

# 注入先ペインの状態を1関数で判定する共有ガード(acquire/banner-wait/inject の3ループで
# 重複していた is_claude_pane + is_working の対を集約・Issue #240 C2)。返り値で状態を返す:
#   0 = OK(claude ペイン生存 & アイドル=注入して良い)
#   1 = ペイン消失 or 前景が claude 系でない(注入不可)
#   2 = 既に WORKING(別経路で再開済み=割り込まない)
# ペイン判定は共有ガード lib-pane-guard.sh の rl_is_claude_pane を直接呼ぶ(薄いラッパは廃止・
# Issue #240 C4)。is_working(=フッタの中断ヒント)はペインが消えていると capture 空で
# false になり「アイドル」と誤判定するため、必ず前景コマンド判定を先に置く。
pane_guard() {
  rl_is_claude_pane "$PANE" || return 1
  is_working && return 2
  return 0
}

# --- リセット時刻をペインテキストから抽出し stdout へ echo する ---
#   週次上限(曜日付き) -> "WEEKLY" / 時刻抽出成功 -> epoch(数字) / それ以外 -> 空。
#   ※ 呼び出しは $(...) 命令置換=サブシェルなので、結果はグローバル変数でなく stdout で返す
#     (サブシェル内のグローバル代入は親に伝播しないため)。
parse_reset_from_text() {
  local text="$1" hhmm now cand
  # 週次上限(曜日付き)。`resets Mon` / `resets at Mon` 双方を拾う(Issue #240 B2)。
  if printf '%s' "$text" | grep -qiE 'resets[[:space:]]+(at[[:space:]]+)?(mon|tue|wed|thu|fri|sat|sun)'; then
    printf 'WEEKLY'
    return 0
  fi
  # `resets 3pm`(数字直後)に加え `resets at 3pm` / `limit resets at 11:59pm` も拾う(Issue #240 B2)。
  hhmm="$(printf '%s' "$text" \
    | grep -oiE 'resets[[:space:]]+(at[[:space:]]+)?[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)' \
    | tail -n1 \
    | grep -oiE '[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)')"
  [ -n "$hhmm" ] || return 0
  now="$(date +%s)"
  cand="$(date -d "today $hhmm" +%s 2>/dev/null || true)"
  [ -n "$cand" ] || return 0
  # cand が過去のときは基本的に「翌日のリセット」だが、リセット直後の数秒(バナーがまだ残る
  # 時間帯)だと今日の時刻が僅かに過去になり、翌日へロールして約24時間 sleep する退化が起きる。
  # 過去 ROLLOVER_GRACE 秒以内は「今まさにリセット」とみなし tomorrow へロールしない(Issue #240 B3)。
  # それより古い過去は本当に翌日のリセットなので tomorrow へ送る。
  if [ "$cand" -le "$now" ] && [ "$(( now - cand ))" -gt "$ROLLOVER_GRACE" ]; then
    cand="$(date -d "tomorrow $hhmm" +%s 2>/dev/null || true)"
  fi
  printf '%s' "$cand"
}

# --- ②再開プロンプトへ検知/解除/現在時刻・解除済みの旨を明記する ---
# LLM が「さっきレートリミットに当たったから」と誤って未解除のまま思い込み、サブエージェント
# 利用等の通常プロセスから逸脱する事象への対策。CLAUDE_RL_CONTINUE_MSG が明示指定されていれば
# そのまま使う(運用者の意図を優先)。未指定時は、①が状態ファイルへ記録した検知時刻(HIT_STR・
# 取得できたもののみ)・解除時刻(reset_epoch があるときのみ)・現在時刻・解除済みである旨を
# 組み立てる。この送信メッセージは Enter で実際に送信されるため、検知時刻が LLM の文脈に入る。
build_continue_msg() {
  local now_str reset_str parts
  if [ -n "$CONTINUE_MSG_OVERRIDE" ]; then
    printf '%s' "$CONTINUE_MSG_OVERRIDE"
    return 0
  fi
  now_str="$(date '+%H:%M:%S')"
  # 取得できた時刻の節だけを並べる(未取得の節は出さない=同値の重複や虚偽の時刻を避ける)。
  parts=""
  [ -n "${HIT_STR:-}" ] && parts="検知 ${HIT_STR}／"
  if [ -n "${reset_epoch:-}" ]; then
    reset_str="$(date -d "@${reset_epoch}" '+%H:%M:%S' 2>/dev/null || true)"
    [ -n "${reset_str:-}" ] && parts="${parts}解除 ${reset_str} ごろ／"
  fi
  parts="${parts}現在 ${now_str}"
  # Issue #502: 復帰時の worktree 掃引の結果があれば1文だけ添える(未実施/対象なしのときは空)。
  # 主文脈が「異常終了した dispatch の worktree が解放済みかどうか」を知らずに再投入すると、
  # adopt-branch の失敗を見て初めて気づくことになるため、復帰メッセージ自体に載せる。
  printf 'レートリミットは解除されました(%s)。制限は解除済みです。サブエージェント利用などの通常プロセスに戻って続けてください。%s' "$parts" "${SWEEP_MSG:-}"
}

# hit-file(1行目=検知時の session_id・2行目=検知時刻)から、自 session と一致する検知時刻だけを
# stdout へ返す(D1)。不一致(別セッション/別エピソードの stale)または時刻空なら何も出さない。
# ファイル側 session_id が空のときは照合をスキップ=採用(後方互換)。旧1行形式(1行目=時刻・
# 2行目無し)は 2行目が空になり時刻空とみなして破棄される。ファイル読み取りのみの純関数で、
# consume(削除)やログは呼び出し側が行う=テスト用フックで公開して直接検証できる(Issue #240 M1/D2)。
resolve_hit_str() {
  local file="$1" my_sid="$2" fsid ftime
  [ -f "$file" ] || return 0
  fsid="$(sed -n '1p' "$file" 2>/dev/null || true)"
  ftime="$(sed -n '2p' "$file" 2>/dev/null || true)"
  if [ -n "$ftime" ] && { [ -z "$fsid" ] || [ "$fsid" = "$my_sid" ]; }; then
    printf '%s' "$ftime"
  fi
}

# テスト用フック(Issue #240 D2): CLAUDE_RL_SOURCE_FOR_TEST=1 で source されたら、ここまでに
# 定義した純ロジック関数(parse_reset_from_text / build_continue_msg / is_limit_screen /
# text_has_banner など)だけを公開して return する。ロック取得・待機・注入といった副作用のある
# 本体は実行しないため、tmux 非依存で Python unittest から直接検証できる(Codex 側
# codex-rate-limit-watcher.sh の CODEX_RL_SOURCE_FOR_TEST と同方式)。
if [ "${CLAUDE_RL_SOURCE_FOR_TEST:-0}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

# --- Issue #502: 復帰イベントに相乗りする worktree 掃引 ---
# 異常終了(レートリミット/セッション上限による強制停止)では SubagentStop が発火せず、
# worktree 所有台帳の entry が `running` のまま残り、worktree も対象ブランチを掴んだままになる。
# その状態では次の dispatch の `gitgate adopt-branch` が必ず BRANCH_ADOPT_LOCAL_EXISTS で失敗し、
# 主文脈が手作業で解放するまで是正ループが止まる(Issue #502 観測1)。
#
# **検知経路は二重化しない**(オーナー指示 2026-09-08)。異常終了の主因はレートリミットなので、
# 復帰の契機は既にここにある「解除を確認し、かつペインがアイドル」という観測に相乗りさせる。
# 当該ペインがアイドル = このペインからは何のサブエージェントも実行中でない、という観測が、
# `running` の2つの意味(入れ子委譲待ちの正当な保留 = Issue #423 / 異常終了の取り残し)を分ける
# 唯一の材料である。その観測を `--no-live-dispatch` として gitgate へ明示的に渡す(これが無いと
# gitgate 側は何もしない = 誤って普通の経路から呼んでも #423 の保留を壊さない)。
#
# **観測の届く範囲は `$PANE` ただ1つ**(F-502-02)。`pane_guard` は引数で渡されたこのペインしか
# 見ないのに対し、worktree 所有台帳はリポジトリ全体で共有される。したがって別ペイン・別セッション
# で live な dispatch が動いていても `--no-live-dispatch` は真になりうる。そこを守るのは gitgate
# 側の `git worktree list --porcelain` の `locked` 判定だけであり、ハーネスが live な agent
# worktree をロックしない構成ではクロスペインの保護は成立しない(その場合は
# CLAUDE_RL_SWEEP_WORKTREES=0 で掃引を止める)。
#
# 掃引自体は best-effort。失敗しても watcher の本務(再開注入)は続ける。
REPO_ROOT="$(cd "${HOOK_DIR}/../.." 2>/dev/null && pwd)"
SWEEP_MSG=""
SWEEP_DONE=0
# 掃引全体の上限秒(F-502-06)。掃引は候補ごとに `git fetch`(各30秒上限)を回すため、候補数に
# 比例して所要時間が伸びる。アイドル判定と send-keys の間隔が青天井に広がると、その間に
# 再開したセッションへ割り込みうるので、掃引側にも上限を掛けて間隔を有界にする。
SWEEP_TIMEOUT="${CLAUDE_RL_SWEEP_TIMEOUT:-120}"
# 非数値は既定へ倒す(この値は非クォートで展開して `timeout` の引数列に混ぜるため、
# 数字だけであることを構文で保証してから使う)。
case "$SWEEP_TIMEOUT" in
  ''|*[!0-9]*) SWEEP_TIMEOUT=120 ;;
esac
sweep_abandoned_worktrees() {
  [ "${CLAUDE_RL_SWEEP_WORKTREES:-1}" = "0" ] && { log "worktree sweep: 無効化されています(CLAUDE_RL_SWEEP_WORKTREES=0)"; return 0; }
  [ "$SWEEP_DONE" -eq 1 ] && return 0
  SWEEP_DONE=1
  if [ -z "${REPO_ROOT}" ] || [ ! -d "${REPO_ROOT}/gitgate" ]; then
    log "worktree sweep: リポジトリルートを特定できず(REPO_ROOT='${REPO_ROOT}'); skip"
    return 0
  fi
  local out rc reason limiter
  reason="resume-watcher: レートリミット解除を確認し当該ペインがアイドル(このペインに live な dispatch 無し)の地点で掃引した (Issue #502)"
  # `timeout` があれば必ず被せる(-k 5 は rl_tmux と同じ考え方=SIGTERM を無視するプロセスを
  # 5秒後に SIGKILL)。無い環境では上限なしでそのまま起動する(掃引を落とすより実行する側に倒す
  # ——後段の pane_guard 再評価が割り込みは防ぐ)。**起動口は1箇所に保つ**(検知経路の二重化を
  # 静的検査で禁じているため、timeout の有無で gitgate の起動行そのものを分岐させない)。
  if command -v timeout >/dev/null 2>&1; then
    limiter="timeout -k 5 $SWEEP_TIMEOUT"
  else
    limiter=""
    log "worktree sweep: timeout コマンドが無いため上限を掛けられない(そのまま起動する)"
  fi
  # shellcheck disable=SC2086 # limiter は上で組み立てた固定語の並び。分割されること自体が意図。
  out="$(cd "$REPO_ROOT" && $limiter python3 -m gitgate worktree-sweep-abandoned \
    --no-live-dispatch --reason "$reason" 2>&1)"
  rc=$?
  [ "$rc" -eq 124 ] && log "worktree sweep: ${SWEEP_TIMEOUT}s で打ち切った(timeout)"
  log "worktree sweep: rc=${rc} ${out}"
  if [ "$rc" -eq 0 ]; then
    # 処置が要る側(kept-)を優先して知らせる。両方あるときに "解放しました" だけを出すと、
    # 残っている方を主文脈が見落とす。`release-pending` は `released` の部分文字列ではない
    # ので独立の枝が要る(F-502-07: 拾い漏れると回収済み・削除遅延だけ1文が付かなかった)。
    case "$out" in
      *"action=kept-"*)
        SWEEP_MSG="なお、running のまま残っていた agent worktree のうち自動解放できなかったものがあります(Issue #502)。tmp/_worktree/ledger.json の notes を確認し、ISSUE_START_WORKTREE_RESIDUE の解消手順で処置してください。"
        ;;
      *"action=release-pending"*)
        SWEEP_MSG="なお、異常終了で running のまま残っていた agent worktree の handoff を復帰時に回収しました(Issue #502)。worktree 実体の削除は git のロックで遅延しており、次の dispatch で issue-start-gate が引き取ります。詳細は ~/.claude/rate-limit-recovery/watcher.log と tmp/_worktree/ledger.json の notes を参照してください。"
        ;;
      *"action=released"*)
        SWEEP_MSG="なお、異常終了で running のまま残っていた agent worktree を復帰時に自動回収・解放しました(Issue #502)。詳細は ~/.claude/rate-limit-recovery/watcher.log と tmp/_worktree/ledger.json の notes を参照してください。"
        ;;
    esac
  fi
  return 0
}

# --- 多重起動防止(同一ペインに watcher は1つだけ) ---
# fd オープン失敗と lock 取得失敗を区別する(Issue #240 B4)。旧実装は `exec 9>… || true` で
# オープン失敗を握り潰していたため、fd 9 が未オープンのまま `flock -n 9` が失敗し「既に起動中」と
# 誤判定して唯一の watcher を殺していた。オープンできなければロック無しで続行(排他は諦めるが
# watcher は起動する)。flock が無い環境も同様にロック無しで続行し、警告だけ残す。
if exec 9>"$LOCK" 2>/dev/null; then
  if command -v flock >/dev/null 2>&1; then
    if ! flock -n 9; then
      log "another watcher already running for this pane; exit"
      exit 0
    fi
  else
    log "flock 不在のため排他ロックなしで続行(同一ペインで二重注入し得る)"
  fi
else
  log "ロックファイル ${LOCK} をオープンできず; 排他ロックなしで続行"
fi

log "start session='${SESSION_ID}'"

# ①が状態ファイルへ記録した検知時刻を「起動直後に読み取り即削除」で消費する。
# ここで消費する理由(待機ループの後ではなく前で行う):
#   - この後のリセット待機は数時間に及び得る。待機後に読むと、その間に発生した別エピソードの
#     ①が同じファイルを上書きし、こちらが別エピソードの検知時刻を誤って表示してしまう。
#   - 早期 exit(ペイン消失/週次上限/バナー未消滅 等)する経路でも、起動時に消費・削除して
#     おけば古い値がファイルに残らず、後続エピソードへ持ち越さない。
# flock 取得済みの単一 watcher でのみここへ到達するため競合しない。
# hit-file は 1行目=検知時の session_id・2行目=検知時刻 の2行形式(on-rate-limit.sh・D1)。
# 自分の SESSION_ID と照合し、不一致(別セッション/別エピソードが残した stale なファイル)なら
# 検知時刻を破棄する。これが無いと、setsid での watcher 起動自体が失敗した/後続エピソードで
# CLAUDE_RL_ANNOUNCE_HIT=0 に切替えた等の経路で、過去の検知時刻を後続 watcher が読んで
# 誤った「検知時刻」を LLM に提示し得る(Issue #240 D1)。
# ファイル側 session_id が空(検知時に session_id を抽出できなかった)ときは照合をスキップ=採用
# (後方互換)。読み終えたら consume+delete して後続へ持ち越さない。
HIT_STR=""
_hit_file="$(rl_hit_file "$PANE")"
if [ -f "$_hit_file" ]; then
  # session 照合(D1)は純関数 resolve_hit_str に委譲(テストで直接検証・M1)。consume は必ず行う。
  HIT_STR="$(resolve_hit_str "$_hit_file" "$SESSION_ID")"
  rm -f "$_hit_file" 2>/dev/null || true
  if [ -n "$HIT_STR" ]; then
    log "検知時刻を状態ファイルから取得: '${HIT_STR}'"
  else
    log "hit-file の session 不一致(watcher='${SESSION_ID}') または時刻空; 検知時刻を破棄"
  fi
fi

# --- リセット時刻を「取り逃したら再取得」する ---
# 旧実装は起動直後に1回だけ capture していたため、レート制限バナーが未描画(=watcher が
# バナー出現より先に起動する競合)だとリセット時刻を取り逃し、盲目の既定待機で"早撃ち"していた。
# ここでは時刻を取得できるまで短間隔で再取得し、当てずっぽうの時刻発火はしない。
reset_epoch=""
saw_banner=0
i=1
while [ "$i" -le "$RESET_POLL_MAX" ]; do
  # 途中でセッション再開/ペイン消失を検知したら注入せず終了(誤送出防止・共有ガード pane_guard)
  pane_guard; _g=$?
  if [ "$_g" -eq 1 ]; then log "acquire: 対象ペインが消失 or 前景が claude でない; 注入せず終了"; exit 0; fi
  if [ "$_g" -eq 2 ]; then log "acquire: ペインが既に WORKING(別経路で再開済み); 注入せず終了"; exit 0; fi
  text="$(rl_tmux capture-pane -p -t "$PANE" 2>/dev/null | tail -n "$BANNER_SCAN_LINES")"
  text_has_banner "$text" && saw_banner=1   # 同一スナップショットで判定(再 capture しない)
  parsed="$(parse_reset_from_text "$text")"
  if [ "$parsed" = "WEEKLY" ]; then
    log "weekly limit detected; auto-resume非対応のため待機/注入せず終了"
    exit 0
  fi
  if [ -n "$parsed" ]; then
    reset_epoch="$parsed"
    log "acquire: リセット時刻を取得 (attempt ${i}/${RESET_POLL_MAX}) -> epoch=${reset_epoch}"
    break
  fi
  log "acquire: リセット時刻 未取得 (attempt ${i}/${RESET_POLL_MAX}; banner_seen=${saw_banner}); ${RESET_POLL_INTERVAL}s 後に再取得"
  sleep "$RESET_POLL_INTERVAL"
  i=$(( i + 1 ))
done

# --- 待機方式の決定(当てずっぽうの時刻発火はしない) ---
if [ -n "$reset_epoch" ]; then
  now="$(date +%s)"
  wait_s=$(( reset_epoch - now + MARGIN ))
  [ "$wait_s" -lt 0 ] && wait_s=0
  log "sleeping ${wait_s}s until reset (+${MARGIN}s margin)"
  sleep "$wait_s"
elif [ "$saw_banner" -eq 1 ]; then
  # 時刻は最後まで取れなかったが、制限バナーは観測した=実際にレート制限中。
  # 盲目の時刻発火はせず、バナーが「消える(=リセット発生)」まで待ってから注入する(決定論)。
  log "リセット時刻を ${RESET_POLL_MAX} 回試行しても取得できず。バナー消滅(=リセット)を待つ方式へフォールバック"
  # バナー消滅は「2連続」で確認してから注入する(単発の再描画/部分キャプチャで一瞬バナーが
  # 欠けたのを誤ってリセットと見なし、制限中に早撃ちするのを防ぐ)。
  clear_streak=0
  j=1
  while [ "$j" -le "$BANNER_POLL_MAX" ]; do
    pane_guard; _g=$?
    if [ "$_g" -eq 1 ]; then log "banner-wait: ペイン消失/非claude; 終了"; exit 0; fi
    if [ "$_g" -eq 2 ]; then log "banner-wait: ペインが WORKING(再開済み); 注入せず終了"; exit 0; fi
    if is_limit_screen; then
      clear_streak=0
    else
      clear_streak=$(( clear_streak + 1 ))
      if [ "$clear_streak" -ge 2 ]; then
        log "banner-wait: 制限バナー消滅を2連続確認(=リセット) after ${j} polls; 注入へ"
        break
      fi
    fi
    sleep "$BANNER_POLL_INTERVAL"
    j=$(( j + 1 ))
  done
  if [ "$j" -gt "$BANNER_POLL_MAX" ]; then
    log "banner-wait: 上限まで待ってもバナーが消えず; 当てずっぽう注入はせず終了"
    exit 0
  fi
else
  # バナーを一度も観測できなかった=レート制限画面ではない/既に解消済みの可能性。当てずっぽうに注入しない。
  log "制限バナーを一度も観測できず(${RESET_POLL_MAX} 回試行); 当てずっぽう注入はせず終了"
  exit 0
fi

# --- 注入(状態認識・リセット後のアイドルへ単発注入) ---
# 大原則: リセット待機後、ペインが「作業中でない(アイドル)」なら継続メッセージを注入して再開する。
#   稼働中セッションへの割り込みは is_working ガードだけで防ぐ(=フッタの中断ヒントで判定)。
#   ※ is_limit_screen は情報ログのみ。リセット後は制限バナーが消えるため、これを注入の
#     必須条件にすると「バナー無し=再開済み」と誤認して永遠に注入しない(旧バグ・是正)。
# 既定は単発(MAX_ATTEMPTS=1)。効かないとき用の再試行は >1 で有効化。
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  # 注入前ガード0: ペインが生存し前景が claude 系か。ペインが閉じている/シェルに戻っていると
  # is_working が capture 空で false になり「アイドル」と誤判定して "続けて" をシェルへ誤送出するため、
  # 前景コマンドで確定的にガードする(最優先)。
  pane_guard; _g=$?
  if [ "$_g" -eq 1 ]; then
    cur="$(rl_tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null || true)"
    log "target pane missing or foreground is not claude (current='${cur}'); NOT injecting; exit"
    exit 0
  fi
  # 注入前ガード1: もう動いている(稼働中)なら絶対に割り込まない
  if [ "$_g" -eq 2 ]; then
    log "pane is WORKING (already resumed & active); NOT injecting; exit"
    exit 0
  fi
  # アイドル → 注入して再開(制限バナーの有無は問わない。情報としてのみ記録)
  # 掃引は注入の**直前**に1度だけ行う(Issue #502): ここは「解除済み」かつ「当該ペインがアイドル
  # = このペインに live な dispatch が無い」ことを両方観測できた地点で、その観測こそが
  # 「異常終了で取り残された running」と「入れ子委譲待ちの running(#423)」を分ける材料である。
  sweep_abandoned_worktrees
  # 注入前ガード2(掃引後の再評価・F-502-06): 掃引はネットワーク I/O を含み秒〜分オーダーに
  # なりうる。上のアイドル判定と本文送出の間隔がそのぶん広がるため、掃引の**あとで**もう一度
  # ペイン状態を確かめてから注入する。大原則「稼働中セッションへは絶対に割り込まない」は、
  # 判定と送出の間隔が広がるほど守りにくくなるので、間隔を空けた側で必ず取り直す。
  pane_guard; _g=$?
  if [ "$_g" -eq 1 ]; then
    log "post-sweep: 対象ペインが消失 or 前景が claude でない; 注入せず終了"
    exit 0
  fi
  if [ "$_g" -eq 2 ]; then
    log "post-sweep: 掃引中にペインが WORKING へ遷移(別経路で再開済み); 注入せず終了"
    exit 0
  fi
  msg="$(build_continue_msg)"
  if is_limit_screen; then
    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: idle & limit banner still visible; send '${msg}'"
  else
    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: idle & banner cleared (post-reset); send '${msg}'"
  fi
  # out-of-band 方式のため入力欄に我々の書き込みは無い。よって注入前クリア(C-u)はしない
  # =ユーザーが手打ち中のテキストを消さない(元の設計に一致)。継続メッセージのみ送出する。
  # -l で常にリテラル送出(CLAUDE_RL_CONTINUE_MSG に "Enter"/"C-c" 等のキー名が入っても
  # キーとして誤解釈せず文字列として打つ)。-- でオプション終端を明示し、msg が "-" 始まり
  # でも tmux にフラグ誤認されないようにする。
  # Enter は「本文送出が成功したときだけ」送る。本文送出に失敗したのに Enter を撃つと、
  # 入力欄に既にあった内容(空/ユーザーの手打ち)を誤って送信してしまうため。
  if rl_tmux send-keys -t "$PANE" -l -- "$msg" 2>>"$LOG"; then
    sleep 1
    rl_tmux send-keys -t "$PANE" Enter 2>>"$LOG"
  else
    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: 本文送出に失敗; Enter は送らない"
  fi
  sleep "$VERIFY_WAIT"

  # 注入後の確認: 作業中になった → 再開成功
  if is_working; then
    log "resume confirmed (pane now working); done"
    exit 0
  fi

  # まだアイドル=注入が効いていない(早撃ち/未リセット等)。リトライ可なら待って再試行。
  # 注意: 注入自体は送出済みのため、ここで give up してもメッセージは既にペインに入っている。
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    log "still idle after attempt ${attempt} (message already sent); attempts exhausted; exit"
    exit 0
  fi
  back=$(( RETRY_BACKOFF * attempt ))
  log "still idle; backoff ${back}s then retry (only if still idle & not working)"
  sleep "$back"
  attempt=$(( attempt + 1 ))
done
exit 0
