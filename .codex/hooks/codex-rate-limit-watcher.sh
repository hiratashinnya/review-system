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
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HOOK_DIR}/../.." && pwd)"

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
NODE_WRAPPER_RE="${CODEX_RL_NODE_WRAPPER_RE:-^node$}"
STARTUP_WAIT="${CODEX_RL_STARTUP_WAIT:-30}"

# --- Rate-limit banner detection (Issue #182) -----------------------------
# Detection requires BOTH a limit-hit phrase AND a reset/retry cue to be
# present (AND, not one broad OR) so that ordinary pane text merely
# mentioning "rate limit" / "usage limit" / "too many requests" does not
# false-fire the recovery flow (which ends in an unattended `continue`
# injection). Kept identical to codex-rate-limit-stop-hook.sh's regex so the
# Stop hook's initial gate and this watcher's own pane scanning agree on what
# counts as a real banner. Both halves are overridable via env.
# NOTE: the `{n,m}` interval quantifiers below must NOT be written directly
# inside a `${VAR:-default}` expansion — bash's word-scanner for `${...}`
# treats the default text's *first* unescaped `}` as the end of the whole
# expansion (verified: `${FOO:-a{0,20}b}` evaluates to `a{0,20b}`, silently
# truncating and corrupting the regex). Define the literal default first,
# then apply the env override against that plain variable.
_RATE_LIMIT_PHRASE_RE_DEFAULT='(hit|reached|exceeded)[[:space:]]+(your|the)[[:space:]]+[a-z0-9 -]*(rate|usage|session|request|5-hour|weekly|daily|account)[a-z0-9 -]*limit|(rate|usage|session|request)[ -]?limit[[:space:]]+(reached|exceeded)|429[^0-9]{0,20}too many requests'
_RATE_LIMIT_RESET_RE_DEFAULT='resets?[[:space:]]+([0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)|mon|tue|wed|thu|fri|sat|sun)|try again[^0-9]{0,20}[0-9]|retry[[:space:]]+(in|after)[^0-9]{0,10}[0-9]'
RATE_LIMIT_PHRASE_RE="${CODEX_RL_RATE_LIMIT_PHRASE_RE:-$_RATE_LIMIT_PHRASE_RE_DEFAULT}"
RATE_LIMIT_RESET_RE="${CODEX_RL_RATE_LIMIT_RESET_RE:-$_RATE_LIMIT_RESET_RE_DEFAULT}"
WEEKLY_RE='resets?[[:space:]]+(mon|tue|wed|thu|fri|sat|sun)|weekly limit'
WORKING_RE='to interrupt|interrupt\)|interrupt to|ctrl\+c to (stop|interrupt)|press esc to interrupt|esc to interrupt'

log() { printf '%s [watcher %s] %s\n' "$(date '+%F %T')" "$PANE" "$*" >> "$LOG" 2>/dev/null || true; }

pane_text() { tmux capture-pane -p -t "$PANE" 2>/dev/null; }
pane_tail() { pane_text | tail -n "${1:-12}"; }

is_codex_pane() {
  local cmd path
  cmd="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null)" || return 1
  [ -n "$cmd" ] || return 1
  printf '%s' "$cmd" | grep -qiE -- "$PANE_CMD_RE"
  if [ "$?" -eq 0 ]; then
    return 0
  fi

  # npm/npx Codex installs can leave node as the foreground command. Treat that
  # as safe only for panes rooted in this trusted repository.
  if printf '%s' "$cmd" | grep -qiE -- "$NODE_WRAPPER_RE"; then
    path="$(tmux display-message -p -t "$PANE" '#{pane_current_path}' 2>/dev/null || true)"
    case "$path" in
      "$REPO_ROOT"|"$REPO_ROOT"/*) return 0 ;;
    esac
  fi
  return 1
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
  local text
  text="$(pane_tail 50)"
  text_has_rate_limit_banner "$text"
}

text_has_rate_limit_banner() {
  printf '%s' "$1" | grep -qiE "$RATE_LIMIT_PHRASE_RE" \
    && printf '%s' "$1" | grep -qiE "$RATE_LIMIT_RESET_RE"
}

parse_reset_from_text() {
  local text="$1" now cand hhmm rel value unit json_epoch

  json_epoch="$(json_reset_epoch_from_text "$text")"
  if [ -n "$json_epoch" ]; then
    printf '%s' "$json_epoch"
    return 0
  fi

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

json_reset_epoch_from_text() {
  command -v python3 >/dev/null 2>&1 || return 0
  printf '%s' "$1" | python3 -c '
import json
import re
import sys
import time

text = sys.stdin.read()
now = int(time.time())
vals = []

for match in re.finditer(r"\"resets_at\"\s*:\s*([0-9]{9,12})", text):
    vals.append(int(match.group(1)))

for line in text.splitlines():
    line = line.strip()
    if not line or "rate_limits" not in line:
        continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for key, value in cur.items():
                if key == "resets_at" and isinstance(value, (int, float)):
                    vals.append(int(value))
                elif isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(cur, list):
            stack.extend(cur)

future = sorted(v for v in vals if v >= now - 60)
if future:
    print(future[0])
'
}

wait_for_reset_and_recover() {
  local initial_text="${1:-}" reset_epoch="" saw_banner=0 banner_streak=0 text parsed i now wait_s clear_streak j

  # initial_text (when present) is the /status capture the Stop hook already
  # requested specifically to confirm the pane-tail candidate that made it
  # send /status in the first place — i.e. it is itself a second, independent
  # confirmation (different command, different snapshot), not a single guess.
  # Only trust it, and only try to parse a reset time out of it, if it
  # independently re-matches the AND banner regex on this same snapshot
  # (Issue #182: previously parse_reset_from_text ran unconditionally here,
  # so a stray HH:MMam/pm-shaped substring anywhere in the Stop payload could
  # set reset_epoch without any limit-banner confirmation at all).
  if [ -n "$initial_text" ] && text_has_rate_limit_banner "$initial_text"; then
    saw_banner=1
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
  elif [ -n "$initial_text" ]; then
    log "acquire: status text does not confirm a rate-limit banner; falling back to pane polling"
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
    # Only attempt to extract a reset time from a snapshot that itself
    # confirms the banner (same-snapshot AND), so a later unrelated line
    # containing a clock-like substring cannot set reset_epoch on its own.
    # saw_banner (used by the no-reset-time fallback below) additionally
    # requires the banner to reappear on 2 consecutive polls before it is
    # trusted, as one more confirmation step before the riskier
    # wait-for-banner-to-clear fallback is armed.
    if text_has_rate_limit_banner "$text"; then
      banner_streak=$(( banner_streak + 1 ))
      if [ "$banner_streak" -ge 2 ]; then
        saw_banner=1
      fi
      parsed="$(parse_reset_from_text "$text")"
    else
      banner_streak=0
      parsed=""
    fi
    if [ "$parsed" = "WEEKLY" ]; then
      log "weekly limit detected; automatic recovery is not attempted"
      return 0
    fi
    if [ -n "$parsed" ]; then
      reset_epoch="$parsed"
      log "acquire: reset time parsed on attempt ${i}/${RESET_POLL_MAX}: epoch=${reset_epoch}"
      break
    fi

    log "acquire: reset time not found (attempt ${i}/${RESET_POLL_MAX}; banner_seen=${saw_banner}; banner_streak=${banner_streak})"
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

# Allow this file to be `source`d (with CODEX_RL_SOURCE_FOR_TEST=1) so a unit
# test can call the pure text-matching functions above (text_has_rate_limit_
# banner, parse_reset_from_text, ...) directly against sample text, without
# running the tmux/lock-dependent watcher body below.
if [ "${CODEX_RL_SOURCE_FOR_TEST:-0}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

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

continuous_banner_streak=0
while true; do
  if ! is_codex_pane; then
    log "target pane is gone or foreground is not codex; exit"
    exit 0
  fi

  # Extra confirmation step before arming recovery at all (Issue #182):
  # require the (already AND-gated) banner regex to match on 2 consecutive
  # scans, SCAN_INTERVAL seconds apart, rather than acting on a single
  # snapshot. This is on top of, not instead of, the AND phrase+reset regex.
  if ! is_working && has_rate_limit_banner; then
    continuous_banner_streak=$(( continuous_banner_streak + 1 ))
    log "rate-limit banner candidate (streak=${continuous_banner_streak}/2)"
    if [ "$continuous_banner_streak" -ge 2 ]; then
      log "rate-limit banner confirmed on 2 consecutive scans"
      wait_for_reset_and_recover
      continuous_banner_streak=0
    fi
  else
    continuous_banner_streak=0
  fi

  sleep "$SCAN_INTERVAL"
done
