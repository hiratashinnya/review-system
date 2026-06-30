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
MAX_ATTEMPTS="${CLAUDE_RL_MAX_ATTEMPTS:-1}"          # 注入試行上限(既定1=単発。>1で早撃ち救済リトライ)
RETRY_BACKOFF="${CLAUDE_RL_RETRY_BACKOFF:-300}"      # 再注入バックオフ基本間隔秒
VERIFY_WAIT="${CLAUDE_RL_VERIFY_WAIT:-20}"           # 注入後に状態を再確認するまでの待機秒

log() { printf '%s [watcher %s] %s\n' "$(date '+%F %T')" "$PANE" "$*" >> "$LOG" 2>/dev/null || true; }

# --- ペイン状態の判定(入力欄付近の数行だけを見る=スクロールバックの語句で誤爆しない) ---
pane_tail() { tmux capture-pane -p -t "$PANE" 2>/dev/null | tail -n "${1:-4}"; }

# Claude が作業中(=既に再開して動いている)か。中断ヒント等で判定。出たら絶対に注入しない。
# 入力欄フッタ付近(末尾8行)だけを見る=スクロールバックの語句で誤爆しない。
is_working() {
  pane_tail 8 | grep -qiE "to interrupt|interrupt\)|interrupt to|ctrl\+c to (stop|interrupt)"
}

# 今まさにレート制限画面が出ているか(入力欄付近の末尾8行・厳しめパターン)。
# ここが真のときだけ注入を許可する(=制限画面が確認できないなら触らない)。
is_limit_screen() {
  pane_tail 8 | grep -qiE "resets?[[:space:]]+(mon|tue|wed|thu|fri|sat|sun|[0-9])|hit your (session|weekly|usage|5-hour|account) limit|usage limit|/upgrade|upgrade to"
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

# --- 注入(状態認識・fail-safe) ---
# 大原則: 「制限画面が確認できる かつ 作業中でない」ときだけ注入する。
#         少しでも曖昧(作業中/制限画面が無い)なら触らずに止める(=稼働中への割り込み厳禁)。
# 既定は単発(MAX_ATTEMPTS=1)。リセット時刻の早撃ち救済が要るときだけ >1 にする。
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  # 注入前ガード①: もう動いているなら絶対に割り込まない
  if is_working; then
    log "pane appears to be WORKING (already resumed?); NOT injecting; exit"
    exit 0
  fi
  # 注入前ガード②: 制限画面が確認できないなら注入しない(誤爆防止・既に解消/再開済みの可能性)
  if ! is_limit_screen; then
    log "limit screen NOT confirmed (cleared / already resumed); NOT injecting; exit"
    exit 0
  fi

  log "inject attempt ${attempt}/${MAX_ATTEMPTS}: limit screen confirmed & not working; send '${CONTINUE_MSG}'"
  tmux send-keys -t "$PANE" "$CONTINUE_MSG" 2>>"$LOG"
  sleep 1
  tmux send-keys -t "$PANE" Enter 2>>"$LOG"
  sleep "$VERIFY_WAIT"

  # 注入後の確認: 作業中になった or 制限画面が消えた → 再開成功とみなして停止
  if is_working || ! is_limit_screen; then
    log "resume confirmed (working or limit screen gone); done"
    exit 0
  fi

  # まだ制限画面のまま=注入が効いていない(早撃ち等)。リトライ可なら待って“再評価から”やり直す。
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    log "still on limit screen after attempt ${attempt}; attempts exhausted; give up (no further injection)"
    exit 0
  fi
  back=$(( RETRY_BACKOFF * attempt ))
  log "still on limit screen; backoff ${back}s then re-evaluate (re-inject only if still limit screen & not working)"
  sleep "$back"
  attempt=$(( attempt + 1 ))
done
exit 0
