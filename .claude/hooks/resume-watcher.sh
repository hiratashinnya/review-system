#!/usr/bin/env bash
# レートリミット解除後に tmux ペインへ継続メッセージを送出して対話セッションを再開させる watcher。
#
# 呼び出し元: on-rate-limit.sh から setsid で切り離して起動される(WSL 内 + tmux 前提)。
# 引数: $1=tmux ペインID  $2=session_id  $3=transcript_path
#
# 動作:
#   1) ペインのレート制限テキストからリセット時刻を抽出。取り逃したら短間隔で再取得を
#      リトライする(watcher がバナー描画より先に起動する競合対策=当てずっぽうの早撃ち防止)。
#   2) 時刻を取得できたらリセット(+マージン)まで sleep。最後まで取得できず制限バナーだけ
#      観測できた場合は、当てずっぽうに時刻発火せず「バナー消滅(=リセット発生)」まで待つ。
#      バナーを一度も観測できなければ注入しない(誤発火防止)。
#   3) ペインへ継続メッセージ + Enter を送出
#   4) まだ制限中ならバックオフして再送(上限あり)
#
# 設定(すべて環境変数で上書き可):
set -u

PANE="${1:?pane id required}"
SESSION_ID="${2:-}"
TRANSCRIPT="${3:-}"

STATE_DIR="${HOME}/.claude/rate-limit-recovery"
mkdir -p "$STATE_DIR" 2>/dev/null || true
LOG="${STATE_DIR}/watcher.log"
LOCK="${STATE_DIR}/lock.$(printf '%s' "$PANE" | tr -c 'A-Za-z0-9' '_')"

CONTINUE_MSG_OVERRIDE="${CLAUDE_RL_CONTINUE_MSG:-}"  # 明示指定時はそのまま送出(時刻注記なし)。未指定なら②の自動生成文を使う
RESET_POLL_INTERVAL="${CLAUDE_RL_RESET_POLL_INTERVAL:-15}"   # リセット時刻の再取得ポーリング間隔秒
RESET_POLL_MAX="${CLAUDE_RL_RESET_POLL_MAX:-40}"             # 再取得の最大試行回数(15s×40=10分)
BANNER_POLL_INTERVAL="${CLAUDE_RL_BANNER_POLL_INTERVAL:-30}"  # 時刻不明時: バナー消滅を待つ間隔秒
BANNER_POLL_MAX="${CLAUDE_RL_BANNER_POLL_MAX:-720}"          # 同上限(30s×720=6時間の安全上限)
MARGIN="${CLAUDE_RL_MARGIN:-30}"                     # リセット時刻に足すマージン秒
MAX_ATTEMPTS="${CLAUDE_RL_MAX_ATTEMPTS:-1}"          # 注入試行上限(既定1=単発。>1で早撃ち救済リトライ)
RETRY_BACKOFF="${CLAUDE_RL_RETRY_BACKOFF:-300}"      # 再注入バックオフ基本間隔秒
VERIFY_WAIT="${CLAUDE_RL_VERIFY_WAIT:-20}"           # 注入後に状態を再確認するまでの待機秒
PANE_CMD_RE="${CLAUDE_RL_PANE_CMD_RE:-^(claude|node)$}"  # 注入を許可する前景コマンド(完全一致・claude 本体=node 実行。変則環境は env で上書き)

log() { printf '%s [watcher %s] %s\n' "$(date '+%F %T')" "$PANE" "$*" >> "$LOG" 2>/dev/null || true; }

# --- ペイン状態の判定(入力欄付近の数行だけを見る=スクロールバックの語句で誤爆しない) ---
pane_tail() { tmux capture-pane -p -t "$PANE" 2>/dev/null | tail -n "${1:-4}"; }

# Claude が作業中(=既に再開して動いている)か。中断ヒント等で判定。出たら絶対に注入しない。
# 入力欄フッタ付近(末尾8行)だけを見る=スクロールバックの語句で誤爆しない。
is_working() {
  pane_tail 8 | grep -qiE "to interrupt|interrupt\)|interrupt to|ctrl\+c to (stop|interrupt)"
}

# レート制限バナーがペインに見えるか(情報ログ専用・注入の可否判定には使わない)。
# 注意: リセット後はバナーが消えるため、これを注入の必須条件にすると
#   「バナー無し=再開済み」と誤認して永遠に注入しなくなる(旧バグ・自動再開が機能しない)。
# バナーはフッタ入力欄より上に出るため末尾15行を見る(8行では拾い漏れる=リセット時刻抽出の tail -40 と整合)。
LIMIT_BANNER_RE='resets?[[:space:]]+(mon|tue|wed|thu|fri|sat|sun|[0-9])|hit your (session|weekly|usage|5-hour|account) limit|usage limit|/upgrade|upgrade to'
is_limit_screen() {
  pane_tail 15 | grep -qiE "$LIMIT_BANNER_RE"
}
# 既に capture 済みのテキストに対する制限バナー判定(acquire ループで再 capture を避け、
# saw_banner と時刻抽出を同一スナップショットで評価するため)。
text_has_banner() {
  printf '%s' "$1" | grep -qiE "$LIMIT_BANNER_RE"
}

# 注入先ペインが生存し、かつ前景コマンドが claude 系(=node 実行)か。
# ペインが閉じている / シェル等に戻っている場合に "続けて" を誤送出しないためのガード。
# is_working(=フッタの中断ヒント)はペインが消えていると capture 空で false になり
# 「アイドル」と誤判定するため、注入の可否は前景コマンドで確定させる。
is_claude_pane() {
  local cmd
  cmd="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null)" || return 1
  [ -n "$cmd" ] || return 1   # ペインが存在しない/取得不可 → 注入しない
  # -- でパターン終端を明示(PANE_CMD_RE は env で上書き可能=`-`始まりでもオプション誤認しない)
  printf '%s' "$cmd" | grep -qiE -- "$PANE_CMD_RE"
}

# --- 多重起動防止(同一ペインに watcher は1つだけ) ---
exec 9>"$LOCK" 2>/dev/null || true
if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    log "another watcher already running for this pane; exit"
    exit 0
  fi
fi

log "start session='${SESSION_ID}'"

# --- リセット時刻をペインテキストから抽出し stdout へ echo する ---
#   週次上限(曜日付き) -> "WEEKLY" / 時刻抽出成功 -> epoch(数字) / それ以外 -> 空。
#   ※ 呼び出しは $(...) 命令置換=サブシェルなので、結果はグローバル変数でなく stdout で返す
#     (サブシェル内のグローバル代入は親に伝播しないため)。
parse_reset_from_text() {
  local text="$1" hhmm now cand
  if printf '%s' "$text" | grep -qiE 'resets[[:space:]]+(mon|tue|wed|thu|fri|sat|sun)'; then
    printf 'WEEKLY'
    return 0
  fi
  hhmm="$(printf '%s' "$text" \
    | grep -oiE 'resets[[:space:]]+[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)' \
    | tail -n1 \
    | grep -oiE '[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)')"
  [ -n "$hhmm" ] || return 0
  now="$(date +%s)"
  cand="$(date -d "today $hhmm" +%s 2>/dev/null || true)"
  [ -n "$cand" ] || return 0
  [ "$cand" -le "$now" ] && cand="$(date -d "tomorrow $hhmm" +%s 2>/dev/null || true)"
  printf '%s' "$cand"
}

# --- リセット時刻を「取り逃したら再取得」する ---
# 旧実装は起動直後に1回だけ capture していたため、レート制限バナーが未描画(=watcher が
# バナー出現より先に起動する競合)だとリセット時刻を取り逃し、盲目の既定待機で"早撃ち"していた。
# ここでは時刻を取得できるまで短間隔で再取得し、当てずっぽうの時刻発火はしない。
reset_epoch=""
saw_banner=0
i=1
while [ "$i" -le "$RESET_POLL_MAX" ]; do
  # 途中でセッション再開/ペイン消失を検知したら注入せず終了(誤送出防止)
  if ! is_claude_pane; then
    log "acquire: 対象ペインが消失 or 前景が claude でない; 注入せず終了"
    exit 0
  fi
  if is_working; then
    log "acquire: ペインが既に WORKING(別経路で再開済み); 注入せず終了"
    exit 0
  fi
  text="$(tmux capture-pane -p -t "$PANE" 2>/dev/null | tail -n 40)"
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
    if ! is_claude_pane; then log "banner-wait: ペイン消失/非claude; 終了"; exit 0; fi
    if is_working; then log "banner-wait: ペインが WORKING(再開済み); 注入せず終了"; exit 0; fi
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

# --- ②再開プロンプトへ解除時刻・解除済みの旨を明記する ---
# LLM が「さっきレートリミットに当たったから」と誤って未解除のまま思い込み、サブエージェント
# 利用等の通常プロセスから逸脱する事象への対策。CLAUDE_RL_CONTINUE_MSG が明示指定されていれば
# そのまま使う(運用者の意図を優先)。未指定時は解除時刻(reset_epoch があればそれ、無ければ
# 現在時刻)・現在時刻・解除済みである旨を注入直前に毎回組み立てる。
build_continue_msg() {
  local reset_str now_str
  if [ -n "$CONTINUE_MSG_OVERRIDE" ]; then
    printf '%s' "$CONTINUE_MSG_OVERRIDE"
    return 0
  fi
  now_str="$(date '+%H:%M:%S')"
  # reset_epoch が取れていない(バナー消滅待ちにフォールバックした)場合、reset_str を
  # now_str で埋めると「解除時刻」と「現在時刻」が同じ値の重複表示になり、実際の解除時刻を
  # 示すという目的を果たせない。取得できていないときは解除時刻の節ごと省く。
  if [ -n "${reset_epoch:-}" ]; then
    reset_str="$(date -d "@${reset_epoch}" '+%H:%M:%S' 2>/dev/null || true)"
  fi
  if [ -n "${reset_str:-}" ]; then
    printf 'レートリミットは解除されました(解除時刻 %s ごろ／現在時刻 %s)。制限は解除済みです。サブエージェント利用などの通常プロセスに戻って続けてください。' "$reset_str" "$now_str"
  else
    printf 'レートリミットは解除されました(現在時刻 %s)。制限は解除済みです。サブエージェント利用などの通常プロセスに戻って続けてください。' "$now_str"
  fi
}

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
  if ! is_claude_pane; then
    cur="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null || true)"
    log "target pane missing or foreground is not claude (current='${cur}'); NOT injecting; exit"
    exit 0
  fi
  # 注入前ガード1: もう動いている(稼働中)なら絶対に割り込まない
  if is_working; then
    log "pane is WORKING (already resumed & active); NOT injecting; exit"
    exit 0
  fi
  # アイドル → 注入して再開(制限バナーの有無は問わない。情報としてのみ記録)
  msg="$(build_continue_msg)"
  if is_limit_screen; then
    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: idle & limit banner still visible; send '${msg}'"
  else
    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: idle & banner cleared (post-reset); send '${msg}'"
  fi
  # 注入前に入力欄をクリア(C-u)。on-rate-limit.sh が送った①の検知時刻ドラフト等、
  # 残存テキストと連結して1行の壊れたメッセージが送信されるのを防ぐ。
  tmux send-keys -t "$PANE" C-u 2>>"$LOG"
  tmux send-keys -t "$PANE" "$msg" 2>>"$LOG"
  sleep 1
  tmux send-keys -t "$PANE" Enter 2>>"$LOG"
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
