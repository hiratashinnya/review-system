#!/usr/bin/env bash
# StopFailure(rate_limit) フックハンドラ。
#
# 役割:
#   レートリミット検知時に、WSL 環境でだけ「自動再開ウォッチャ(resume-watcher.sh)」を
#   切り離し起動する。クラウド(=非WSL)では何もしない no-op。
#
# 前提となる公式仕様(調査済み):
#   - StopFailure は出力・終了コードが「無視」される。よってフック自身は再開/リトライを
#     制御できない。できるのは副作用(別プロセスの起動・ログ)のみ。
#   - stdin で {session_id, transcript_path, cwd, hook_event_name, ...} を受け取る。
#     error_type のトップレベル文字列フィールドは公式に未確定で、実機では空で届くことを確認した
#     (2026-06-30)。よって発火の絞り込みは settings.json の matcher(=rate_limit)に委ね、
#     本スクリプトでは error_type を必須にしない(空/不明なら matcher を信頼して継続)。
#     リセット時刻は含まれない。
#
# 設計方針:
#   - 環境ゲートは「WSL を積極検知できたときだけ動く」許可リスト方式。
#     検知できない環境(クラウド/その他)は自動的に無害化される。
#   - 再開方式は tmux 端末注入(対話セッションのペインへ "続けて" を送出)。
set -u

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 共有ガード(ペイン判定・tmux timeout ラッパ・ドラフトマーカー)。resume-watcher.sh と共有。
# shellcheck source=lib-pane-guard.sh
source "${HOOK_DIR}/lib-pane-guard.sh"
STATE_DIR="${HOME}/.claude/rate-limit-recovery"
mkdir -p "$STATE_DIR" 2>/dev/null || true
LOG="${STATE_DIR}/hook.log"

log() { printf '%s [hook] %s\n' "$(date '+%F %T')" "$*" >> "$LOG" 2>/dev/null || true; }

# --- stdin JSON を素朴に読む(標準ツールのみ・jq 非依存) ---
payload="$(cat)"
# 実ペイロードの形を学習するため生 stdin を保存する(error_type のフィールド名/値が未確定なため。
# 次回実発火時にここを見れば正しいフィールド名で厳密化できる)。
printf '%s' "$payload" > "${STATE_DIR}/last-payload.json" 2>/dev/null || true
get() {
  printf '%s' "$payload" \
    | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" \
    | head -n1
}
error_type="$(get error_type)"
session_id="$(get session_id)"
transcript_path="$(get transcript_path)"

log "fired error_type='${error_type}' session='${session_id}'"

# 発火の絞り込みは settings.json の matcher(=rate_limit)が error type で既に行う(公式仕様)。
# stdin の error_type は実機で空のことを確認したため(2026-06-30)、ここで rate_limit を必須にすると
# matcher が選んだ本物の rate_limit を取りこぼす(=旧バグ。watcher が一度も起動しなかった原因)。
# よって「明示的に rate_limit 以外と判明したときだけ」スキップし、空/不明は matcher を信頼して継続する。
if [ -n "${error_type}" ] && [ "${error_type}" != "rate_limit" ]; then
  log "error_type='${error_type}' is explicitly non-rate_limit; skip"
  exit 0
fi

# --- 環境ゲート: WSL を積極検知できたときだけ動く(=クラウドでは no-op で無害) ---
is_wsl=0
[ -n "${WSL_DISTRO_NAME:-}" ] && is_wsl=1
grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null && is_wsl=1
if [ "${is_wsl}" -ne 1 ]; then
  log "non-WSL environment detected; no-op (safe on cloud/other)"
  exit 0
fi

# --- tmux 注入方式: claude が動いているペインを特定 ---
pane="${TMUX_PANE:-}"
if [ -z "${TMUX:-}" ] || [ -z "${pane}" ]; then
  log "not inside tmux (TMUX/TMUX_PANE empty); cannot inject keys. abort. (tmux 内で claude を起動してください)"
  exit 0
fi

# --- ①検知時刻をチャット(ペイン)に表示 ---
# LLM が「レートリミットに当たった」事実は認識できても、その後どれだけ時間が経過したかを
# 見失い、解除後もサブエージェント使用等の通常プロセスから逸脱する事象への対策。
# まずは検知した瞬間の時刻を見えるようにする。StopFailure は出力・終了コードが無視されるため、
# tmux ペインへ直接ドラフト注入する(Enter は送らない=まだ解除前に新規ターンを送信して
# 即座に再度レートリミットへ突入するのを防ぐ。あくまで表示のみ)。
# 安全対策(コードレビュー指摘の是正):
#   - 前景が claude 系のときだけ注入(rl_is_claude_pane・共有ガード)。前景がシェル/別
#     プログラムに戻っていると誤爆するため。
#   - ここでは入力欄をクリアしない=検知時に入力欄へ既にあるユーザーの手打ちテキストを
#     消さない。ドラフトはマーカー付きで送り、後段②が「自分のドラフトだけ」を消す。
#   - 多重発火の重なり(2プロセスの送出が交互に混ざり壊れる)を非ブロッキング flock で防止。
#   - tmux 呼び出しは timeout ラップ(rl_tmux)。StopFailure フックの15秒予算内で本来の
#     役目(watcher 起動)まで確実に到達させるため。
if [ "${CLAUDE_RL_ANNOUNCE_HIT:-1}" != "0" ]; then
  if rl_is_claude_pane "$pane"; then
    hit_time="$(date '+%Y-%m-%d %H:%M:%S')"
    ann_lock="${STATE_DIR}/announce-lock.$(printf '%s' "$pane" | tr -c 'A-Za-z0-9' '_')"
    (
      # 同一ペインへの二重発火をシリアライズ。取得できなければ別発火が処理中とみなし
      # 即スキップ(予算も食わない)。サブシェル終了で fd8=ロック自動解放。
      if command -v flock >/dev/null 2>&1; then
        exec 8>"$ann_lock" 2>/dev/null || true
        flock -n 8 2>/dev/null || { log "announce: 別発火が処理中; skip"; exit 0; }
      fi
      # マーカー付きドラフトを単一 send-keys でアトミックに送出(Enter は送らない)。
      rl_tmux send-keys -t "$pane" "${RL_DRAFT_MARKER} ${hit_time} にレートリミットを検知。解除時刻になり次第、自動で継続メッセージを送信します(このメッセージは未送信のドラフトです)。" 2>>"$LOG" || true
      log "announced hit time ${hit_time} to pane=${pane} (draft, Enter not sent)"
    )
  else
    log "pane foreground is not claude; skip hit-time announcement"
  fi
fi

# --- ウォッチャを切り離して起動(フックは即終了。出力は無視されるため fire-and-forget) ---
setsid bash "${HOOK_DIR}/resume-watcher.sh" "${pane}" "${session_id}" "${transcript_path}" \
  >> "${LOG}" 2>&1 < /dev/null &
log "spawned resume-watcher for pane=${pane}"
exit 0
