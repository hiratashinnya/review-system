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

# レート制限バナーがペインに見えるか(情報ログ専用・注入の可否判定には使わない)。
# 注意: リセット後はバナーが消えるため、これを注入の必須条件にすると
#   「バナー無し=再開済み」と誤認して永遠に注入しなくなる(旧バグ・自動再開が機能しない)。
# バナーはフッタ入力欄より上に出るため末尾15行を見る(8行では拾い漏れる=リセット時刻抽出の tail -40 と整合)。
is_limit_screen() {
  pane_tail 15 | grep -qiE "resets?[[:space:]]+(mon|tue|wed|thu|fri|sat|sun|[0-9])|hit your (session|weekly|usage|5-hour|account) limit|usage limit|/upgrade|upgrade to"
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

# --- 注入(状態認識・リセット後のアイドルへ単発注入) ---
# 大原則: リセット待機後、ペインが「作業中でない(アイドル)」なら継続メッセージを注入して再開する。
#   稼働中セッションへの割り込みは is_working ガードだけで防ぐ(=フッタの中断ヒントで判定)。
#   ※ is_limit_screen は情報ログのみ。リセット後は制限バナーが消えるため、これを注入の
#     必須条件にすると「バナー無し=再開済み」と誤認して永遠に注入しない(旧バグ・是正)。
# 既定は単発(MAX_ATTEMPTS=1)。効かないとき用の再試行は >1 で有効化。
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  # 注入前ガード: もう動いている(稼働中)なら絶対に割り込まない
  if is_working; then
    log "pane is WORKING (already resumed & active); NOT injecting; exit"
    exit 0
  fi
  # アイドル → 注入して再開(制限バナーの有無は問わない。情報としてのみ記録)
  if is_limit_screen; then
    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: idle & limit banner still visible; send '${CONTINUE_MSG}'"
  else
    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: idle & banner cleared (post-reset); send '${CONTINUE_MSG}'"
  fi
  tmux send-keys -t "$PANE" "$CONTINUE_MSG" 2>>"$LOG"
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
