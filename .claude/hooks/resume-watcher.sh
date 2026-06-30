#!/usr/bin/env bash
# レートリミット解除後に tmux ペインへ継続メッセージを送出して対話セッションを再開させる watcher。
#
# 呼び出し元: on-rate-limit.sh から setsid で切り離して起動される(WSL 内 + tmux 前提)。
# 引数: $1=tmux ペインID  $2=session_id  $3=transcript_path
#
# 動作:
#   1) ペインのレート制限テキストからリセット時刻を best-effort 抽出
#   2) リセット時刻(+マージン)まで sleep。不明なら既定待機。
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

CONTINUE_MSG="${CLAUDE_RL_CONTINUE_MSG:-続けて}"     # 送出する継続メッセージ
DEFAULT_WAIT="${CLAUDE_RL_DEFAULT_WAIT:-900}"        # リセット時刻不明時の待機秒(既定15分)
MARGIN="${CLAUDE_RL_MARGIN:-30}"                     # リセット時刻に足すマージン秒
MAX_ATTEMPTS="${CLAUDE_RL_MAX_ATTEMPTS:-6}"          # 注入リトライ上限
RETRY_BACKOFF="${CLAUDE_RL_RETRY_BACKOFF:-300}"      # 再注入バックオフ基本間隔秒

log() { printf '%s [watcher %s] %s\n' "$(date '+%F %T')" "$PANE" "$*" >> "$LOG" 2>/dev/null || true; }

# --- 多重起動防止(同一ペインに watcher は1つだけ) ---
exec 9>"$LOCK" 2>/dev/null || true
if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    log "another watcher already running for this pane; exit"
    exit 0
  fi
fi

log "start session='${SESSION_ID}'"

# --- リセット時刻を best-effort 抽出 ---
pane_text="$(tmux capture-pane -p -t "$PANE" 2>/dev/null | tail -n 40)"
reset_epoch=""

if printf '%s' "$pane_text" | grep -qiE 'resets[[:space:]]+(mon|tue|wed|thu|fri|sat|sun)'; then
  # 週次上限(曜日付き)は待機が長すぎるため自動再開の対象外。既定待機にフォールバック。
  log "weekly limit detected; auto-resume非対応のため既定待機にフォールバック"
else
  hhmm="$(printf '%s' "$pane_text" \
    | grep -oiE 'resets[[:space:]]+[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)' \
    | tail -n1 \
    | grep -oiE '[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)')"
  if [ -n "$hhmm" ]; then
    now="$(date +%s)"
    cand="$(date -d "today $hhmm" +%s 2>/dev/null || true)"
    if [ -n "$cand" ]; then
      [ "$cand" -le "$now" ] && cand="$(date -d "tomorrow $hhmm" +%s 2>/dev/null || true)"
      reset_epoch="$cand"
      log "parsed reset time '$hhmm' -> epoch=${reset_epoch}"
    fi
  fi
fi

# --- 待機 ---
now="$(date +%s)"
if [ -n "$reset_epoch" ]; then
  wait_s=$(( reset_epoch - now + MARGIN ))
  [ "$wait_s" -lt 0 ] && wait_s=0
else
  wait_s="$DEFAULT_WAIT"
  log "reset time unknown; using default wait ${wait_s}s"
fi
log "sleeping ${wait_s}s until reset"
sleep "$wait_s"

# --- 注入 + リトライ ---
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  log "inject attempt ${attempt}/${MAX_ATTEMPTS}: send '${CONTINUE_MSG}'"
  tmux send-keys -t "$PANE" "$CONTINUE_MSG" 2>>"$LOG"
  sleep 1
  tmux send-keys -t "$PANE" Enter 2>>"$LOG"
  sleep 20

  after="$(tmux capture-pane -p -t "$PANE" 2>/dev/null | tail -n 15)"
  if printf '%s' "$after" | grep -qiE "hit your (session|weekly|usage) limit|rate limit|resets[[:space:]]"; then
    back=$(( RETRY_BACKOFF * attempt ))
    log "still limited; backoff ${back}s then retry"
    sleep "$back"
    attempt=$(( attempt + 1 ))
  else
    log "resume injected successfully; done"
    exit 0
  fi
done

log "gave up after ${MAX_ATTEMPTS} attempts (still limited)"
exit 0
