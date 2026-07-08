#!/usr/bin/env bash
# Monitor a Codex CLI tmux pane and recover automatically after rate limits.
#
# This is the Codex analogue of resume-watcher.sh, but Codex currently does not
# provide a StopFailure(rate_limit) hook equivalent. It can either run as a
# legacy pane monitor or as a one-shot worker launched by the Stop hook after
# the hook has asked Codex for /status.
set -u

MODE="watch"
STATUS_TEXT_FILE=""
if [ "${1:-}" = "--recover-once" ]; then
  MODE="once"
  PANE="${2:?tmux pane id required}"
  STATUS_TEXT_FILE="${3:-}"
else
  PANE="${1:?tmux pane id required}"
fi

STATE_DIR="${CODEX_RL_STATE_DIR:-${HOME}/.codex/rate-limit-recovery}"
mkdir -p "$STATE_DIR" 2>/dev/null || true
LOG="${STATE_DIR}/watcher.log"
LOCK="${STATE_DIR}/lock.$(printf '%s' "$PANE" | tr -c 'A-Za-z0-9' '_')"

CONTINUE_MSG="${CODEX_RL_CONTINUE_MSG:-continue}"
SCAN_INTERVAL="${CODEX_RL_SCAN_INTERVAL:-20}"
RESET_POLL_INTERVAL="${CODEX_RL_RESET_POLL_INTERVAL:-15}"
RESET_POLL_MAX="${CODEX_RL_RESET_POLL_MAX:-40}"
BANNER_POLL_INTERVAL="${CODEX_RL_BANNER_POLL_INTERVAL:-30}"
BANNER_POLL_MAX="${CODEX_RL_BANNER_POLL_MAX:-720}"
MARGIN="${CODEX_RL_MARGIN:-30}"
MAX_ATTEMPTS="${CODEX_RL_MAX_ATTEMPTS:-1}"
RETRY_BACKOFF="${CODEX_RL_RETRY_BACKOFF:-300}"
VERIFY_WAIT="${CODEX_RL_VERIFY_WAIT:-20}"
PANE_CMD_RE="${CODEX_RL_PANE_CMD_RE:-^codex$}"
STARTUP_WAIT="${CODEX_RL_STARTUP_WAIT:-30}"

RATE_LIMIT_RE='rate[ -]?limit|usage limit|session limit|request limit|too many requests|hit your .*limit|429.*(rate|limit|too many)|resets?[[:space:]]+([0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)|mon|tue|wed|thu|fri|sat|sun)'
WEEKLY_RE='resets?[[:space:]]+(mon|tue|wed|thu|fri|sat|sun)|weekly limit'
WORKING_RE='to interrupt|interrupt\)|interrupt to|ctrl\+c to (stop|interrupt)|press esc to interrupt|esc to interrupt'

log() { printf '%s [watcher %s] %s\n' "$(date '+%F %T')" "$PANE" "$*" >> "$LOG" 2>/dev/null || true; }

pane_text() { tmux capture-pane -p -t "$PANE" 2>/dev/null; }
pane_tail() { pane_text | tail -n "${1:-12}"; }

is_codex_pane() {
  local cmd
  cmd="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null)" || return 1
  [ -n "$cmd" ] || return 1
  printf '%s' "$cmd" | grep -qiE -- "$PANE_CMD_RE"
}

wait_for_codex_pane() {
  local waited=0
  while [ "$waited" -le "$STARTUP_WAIT" ]; do
    if is_codex_pane; then
      return 0
    fi
    sleep 1
    waited=$(( waited + 1 ))
  done
  return 1
}

is_working() {
  pane_tail 10 | grep -qiE "$WORKING_RE"
}

has_rate_limit_banner() {
  pane_tail 50 | grep -qiE "$RATE_LIMIT_RE"
}

text_has_rate_limit_banner() {
  printf '%s' "$1" | grep -qiE "$RATE_LIMIT_RE"
}

parse_reset_from_text() {
  local text="$1" now cand hhmm rel value unit

  if printf '%s' "$text" | grep -qiE "$WEEKLY_RE"; then
    printf 'WEEKLY'
    return 0
  fi

  hhmm="$(printf '%s' "$text" \
    | grep -oiE '(resets?|reset|try again|available again|retry)[^0-9]{0,30}[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)' \
    | tail -n1 \
    | grep -oiE '[0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)' \
    | tail -n1)"
  if [ -n "$hhmm" ]; then
    now="$(date +%s)"
    cand="$(date -d "today $hhmm" +%s 2>/dev/null || true)"
    [ -n "$cand" ] || return 0
    [ "$cand" -le "$now" ] && cand="$(date -d "tomorrow $hhmm" +%s 2>/dev/null || true)"
    printf '%s' "$cand"
    return 0
  fi

  rel="$(printf '%s' "$text" \
    | grep -oiE '(try again|retry|reset|resets?)[^0-9]{0,30}[0-9]+[[:space:]]*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)' \
    | tail -n1)"
  if [ -n "$rel" ]; then
    value="$(printf '%s' "$rel" | grep -oiE '[0-9]+' | tail -n1)"
    unit="$(printf '%s' "$rel" | grep -oiE '(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)' | tail -n1)"
    case "$unit" in
      s|sec|secs|second|seconds) printf '%s' "$(( $(date +%s) + value ))" ;;
      m|min|mins|minute|minutes) printf '%s' "$(( $(date +%s) + value * 60 ))" ;;
      h|hr|hrs|hour|hours) printf '%s' "$(( $(date +%s) + value * 3600 ))" ;;
    esac
  fi
}

wait_for_reset_and_recover() {
  local initial_text="${1:-}" reset_epoch="" saw_banner=0 text parsed i now wait_s clear_streak j

  if [ -n "$initial_text" ]; then
    text_has_rate_limit_banner "$initial_text" && saw_banner=1
    parsed="$(parse_reset_from_text "$initial_text")"
    if [ "$parsed" = "WEEKLY" ]; then
      log "weekly limit detected from status text; automatic recovery is not attempted"
      return 0
    fi
    if [ -n "$parsed" ]; then
      reset_epoch="$parsed"
      log "acquire: reset time parsed from status text: epoch=${reset_epoch}"
    else
      log "acquire: reset time not found in status text; falling back to pane polling"
    fi
  fi

  i=1
  while [ -z "$reset_epoch" ] && [ "$i" -le "$RESET_POLL_MAX" ]; do
    if ! is_codex_pane; then
      log "acquire: target pane missing or foreground is not codex; exit"
      exit 0
    fi
    if is_working; then
      log "acquire: pane is working; skip current recovery cycle"
      return 0
    fi

    text="$(pane_text | tail -n 80)"
    text_has_rate_limit_banner "$text" && saw_banner=1
    parsed="$(parse_reset_from_text "$text")"
    if [ "$parsed" = "WEEKLY" ]; then
      log "weekly limit detected; automatic recovery is not attempted"
      return 0
    fi
    if [ -n "$parsed" ]; then
      reset_epoch="$parsed"
      log "acquire: reset time parsed on attempt ${i}/${RESET_POLL_MAX}: epoch=${reset_epoch}"
      break
    fi

    log "acquire: reset time not found (attempt ${i}/${RESET_POLL_MAX}; banner_seen=${saw_banner})"
    sleep "$RESET_POLL_INTERVAL"
    i=$(( i + 1 ))
  done

  if [ -n "$reset_epoch" ]; then
    now="$(date +%s)"
    wait_s=$(( reset_epoch - now + MARGIN ))
    [ "$wait_s" -lt 0 ] && wait_s=0
    log "sleeping ${wait_s}s until reset (+${MARGIN}s margin)"
    sleep "$wait_s"
  elif [ "$saw_banner" -eq 1 ]; then
    log "reset time unavailable; waiting for rate-limit banner to clear twice"
    clear_streak=0
    j=1
    while [ "$j" -le "$BANNER_POLL_MAX" ]; do
      if ! is_codex_pane; then log "banner-wait: non-codex pane; exit"; exit 0; fi
      if is_working; then log "banner-wait: pane is working; skip injection"; return 0; fi
      if has_rate_limit_banner; then
        clear_streak=0
      else
        clear_streak=$(( clear_streak + 1 ))
        if [ "$clear_streak" -ge 2 ]; then
          log "banner-wait: banner cleared twice after ${j} polls"
          break
        fi
      fi
      sleep "$BANNER_POLL_INTERVAL"
      j=$(( j + 1 ))
    done
    if [ "$j" -gt "$BANNER_POLL_MAX" ]; then
      log "banner-wait: limit banner did not clear; no blind injection"
      return 0
    fi
  else
    log "no rate-limit banner observed during acquire; no injection"
    return 0
  fi

  inject_continue
}

inject_continue() {
  local attempt=1 back cur
  while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    if ! is_codex_pane; then
      cur="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null || true)"
      log "target pane missing or foreground is not codex (current='${cur}'); not injecting"
      exit 0
    fi
    if is_working; then
      log "pane is working; not injecting"
      return 0
    fi

    log "inject attempt ${attempt}/${MAX_ATTEMPTS}: send '${CONTINUE_MSG}'"
    tmux send-keys -t "$PANE" "$CONTINUE_MSG" 2>>"$LOG"
    sleep 1
    tmux send-keys -t "$PANE" Enter 2>>"$LOG"
    sleep "$VERIFY_WAIT"

    if is_working; then
      log "resume confirmed: pane is now working"
      return 0
    fi
    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
      log "still idle after attempt ${attempt}; attempts exhausted"
      return 0
    fi
    back=$(( RETRY_BACKOFF * attempt ))
    log "still idle; backing off ${back}s before retry"
    sleep "$back"
    attempt=$(( attempt + 1 ))
  done
}

exec 9>"$LOCK" 2>/dev/null || true
if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    log "another watcher already running for this pane; exit"
    exit 0
  fi
fi

log "start mode=${MODE}"
if ! wait_for_codex_pane; then
  cur="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null || true)"
  log "codex did not become foreground within ${STARTUP_WAIT}s (current='${cur}'); exit"
  exit 0
fi

if [ "$MODE" = "once" ]; then
  initial_text=""
  if [ -n "$STATUS_TEXT_FILE" ] && [ -r "$STATUS_TEXT_FILE" ]; then
    initial_text="$(cat "$STATUS_TEXT_FILE" 2>/dev/null || true)"
  fi
  wait_for_reset_and_recover "$initial_text"
  exit 0
fi

while true; do
  if ! is_codex_pane; then
    log "target pane is gone or foreground is not codex; exit"
    exit 0
  fi

  if ! is_working && has_rate_limit_banner; then
    log "rate-limit banner detected"
    wait_for_reset_and_recover
  fi

  sleep "$SCAN_INTERVAL"
done
