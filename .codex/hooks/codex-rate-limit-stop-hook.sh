#!/usr/bin/env bash
# Stop hook handler for Codex CLI rate-limit recovery.
#
# Codex Stop hooks run after a turn stops. When the visible Codex pane looks
# rate-limited, this hook asks the TUI for /status, captures the status text,
# and launches the one-shot watcher to wait until the parsed reset time.
set -u

# --- Rate-limit banner detection (Issue #182) ----------------------------
# Detection requires BOTH a limit-hit phrase AND a reset/retry cue to be
# present (AND, not one broad OR) so that ordinary pane text that merely
# mentions "rate limit" / "usage limit" / "too many requests" (very common
# wording while discussing or implementing rate-limiting code, or pasting an
# unrelated HTTP 429 log) does not accidentally trigger `/status` plus the
# auto-resume watcher, whose end effect is an unattended `continue` being
# injected into the pane. Real captured banners always pair the two, e.g.
# "You've hit your session limit \xc2\xb7 resets 10:50pm (Asia/Tokyo)"
# (real payload captured in PR #66). Both halves are overridable via env for
# local tuning without editing this file.
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

has_rate_limit_text() {
  local blob
  blob="$(printf '%s\n%s' "$1" "$2")"
  printf '%s' "$blob" | grep -qiE "$RATE_LIMIT_PHRASE_RE" \
    && printf '%s' "$blob" | grep -qiE "$RATE_LIMIT_RESET_RE"
}

# --- Structured rate-limit API detection (Issue #195) --------------------
# Primary detector. Instead of scraping the rendered tmux banner, ask Codex's
# app-server for the machine-readable account/rateLimits/read snapshot (via the
# codex-rate-limit-query.py helper). The pane-text regex above is kept only as
# a fallback for when this API is unavailable (see the hook body).
RL_QUERY_HELPER="${CODEX_RL_QUERY_HELPER:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/codex-rate-limit-query.py}"
MAX_AUTO_WINDOW_MINS="${CODEX_RL_MAX_AUTO_WINDOW_MINS:-360}"

# Populate RL_* globals from the helper's `RL_KEY=value` output. Returns 0 only
# when the query succeeded (RL_OK=1); a non-zero return tells the caller to fall
# back to text parsing. CODEX_RL_QUERY_CMD overrides the helper invocation for
# tests (it is eval'd and expected to print the same RL_* lines).
query_rate_limit_api() {
  RL_OK=0; RL_REACHED=0; RL_REACHED_TYPE=""; RL_RESET_EPOCH=""
  RL_WINDOW_MINS=""; RL_USED_PERCENT=""; RL_PLAN=""
  local out k v
  if [ -n "${CODEX_RL_QUERY_CMD:-}" ]; then
    out="$(eval "$CODEX_RL_QUERY_CMD" 2>>"${LOG:-/dev/null}")" || true
  else
    command -v python3 >/dev/null 2>&1 || return 1
    [ -r "$RL_QUERY_HELPER" ] || return 1
    out="$(python3 "$RL_QUERY_HELPER" 2>>"${LOG:-/dev/null}")" || true
  fi
  while IFS='=' read -r k v; do
    case "$k" in
      RL_OK) RL_OK="$v" ;;
      RL_REACHED) RL_REACHED="$v" ;;
      RL_REACHED_TYPE) RL_REACHED_TYPE="$v" ;;
      RL_RESET_EPOCH) RL_RESET_EPOCH="$v" ;;
      RL_WINDOW_MINS) RL_WINDOW_MINS="$v" ;;
      RL_USED_PERCENT) RL_USED_PERCENT="$v" ;;
      RL_PLAN) RL_PLAN="$v" ;;
    esac
  done <<RLEOF
$out
RLEOF
  [ "$RL_OK" = "1" ]
}

# True when the binding (reached) window is longer than the auto-recover cap,
# i.e. a weekly/long limit we should not sit and wait on. Unknown/empty window
# durations are treated as "not long" (we still have a concrete resetsAt).
api_window_is_long() {
  case "$RL_WINDOW_MINS" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$RL_WINDOW_MINS" -gt "$MAX_AUTO_WINDOW_MINS" ]
}

# Allow this file to be `source`d (with CODEX_RL_SOURCE_FOR_TEST=1) so a unit
# test can call has_rate_limit_text() directly against sample text, without
# running the tmux-dependent hook body below (which would otherwise exit/act
# on a real pane as soon as it is sourced).
if [ "${CODEX_RL_SOURCE_FOR_TEST:-0}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HOOK_DIR}/../.." && pwd)"
STATE_DIR="${CODEX_RL_STATE_DIR:-${HOME}/.codex/rate-limit-recovery}"
PANE="${CODEX_RL_TMUX_PANE:-${TMUX_PANE:-}}"
PANE_CMD_RE="${CODEX_RL_PANE_CMD_RE:-^codex$}"
NODE_WRAPPER_RE="${CODEX_RL_NODE_WRAPPER_RE:-^node$}"
STATUS_WAIT="${CODEX_RL_STATUS_WAIT:-3}"
STATUS_CAPTURE_LINES="${CODEX_RL_STATUS_CAPTURE_LINES:-140}"
STATUS_ON_EVERY_STOP="${CODEX_RL_STATUS_ON_EVERY_STOP:-0}"
STATUS_COOLDOWN="${CODEX_RL_STATUS_COOLDOWN:-60}"
API_CHECK="${CODEX_RL_API_CHECK:-1}"

say_noop() { printf '%s\n' "$*" >&2; }

is_truthy() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

is_cloud_env() {
  is_truthy "${CODEX_RL_CLOUD:-}" && return 0
  is_truthy "${CODEX_RL_CLOUD_ENV:-}" && return 0
  is_truthy "${CODEX_CLOUD:-}" && return 0
  [ -n "${CODEX_CLOUD_ENVIRONMENT_ID:-}" ] && return 0
  [ -n "${CODEX_ENVIRONMENT_ID:-}" ] && return 0
  return 1
}

if is_cloud_env; then
  say_noop "cloud environment detected by env; no-op"
  exit 0
fi

if [ -z "$PANE" ] || [ -z "${TMUX:-}" ]; then
  say_noop "not inside tmux or TMUX_PANE unavailable; no-op"
  exit 0
fi

if ! command -v tmux >/dev/null 2>&1; then
  say_noop "tmux command unavailable; no-op"
  exit 0
fi

mkdir -p "$STATE_DIR" 2>/dev/null || true
LOG="${STATE_DIR}/stop-hook.log"
LAST_PAYLOAD="${STATE_DIR}/last-stop-payload.json"

log() { printf '%s [stop-hook] %s\n' "$(date '+%F %T')" "$*" >> "$LOG" 2>/dev/null || true; }

pane_text() { tmux capture-pane -p -t "$PANE" 2>/dev/null; }
pane_tail() { pane_text | tail -n "${1:-50}"; }

is_codex_pane() {
  local cmd path
  cmd="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null)" || return 1
  [ -n "$cmd" ] || return 1
  printf '%s' "$cmd" | grep -qiE -- "$PANE_CMD_RE"
  if [ "$?" -eq 0 ]; then
    return 0
  fi

  # Codex installed through npm/npx can appear as a node foreground command.
  # Accept that wrapper only when the pane is sitting in this trusted repo.
  if printf '%s' "$cmd" | grep -qiE -- "$NODE_WRAPPER_RE"; then
    path="$(tmux display-message -p -t "$PANE" '#{pane_current_path}' 2>/dev/null || true)"
    case "$path" in
      "$REPO_ROOT"|"$REPO_ROOT"/*) return 0 ;;
    esac
  fi
  return 1
}

payload="$(cat 2>/dev/null || true)"
printf '%s' "$payload" > "$LAST_PAYLOAD" 2>/dev/null || true

if ! is_codex_pane; then
  cur="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null || true)"
  path="$(tmux display-message -p -t "$PANE" '#{pane_current_path}' 2>/dev/null || true)"
  log "target pane missing or foreground is not codex/node-wrapper (current='${cur}' path='${path}'); no-op"
  exit 0
fi

# --- cooldown gate (shared by the API check and the legacy /status path) --
# One active rate-limit check per pane per STATUS_COOLDOWN seconds, so neither
# launching the app-server nor sending /status happens on every single Stop.
pane_key="$(printf '%s' "$PANE" | tr -c 'A-Za-z0-9' '_')"
cooldown_file="${STATE_DIR}/last-status.${pane_key}"
now="$(date +%s)"
if [ -r "$cooldown_file" ]; then
  last="$(cat "$cooldown_file" 2>/dev/null || true)"
  case "$last" in
    ''|*[!0-9]*) ;;
    *)
      age=$(( now - last ))
      if [ "$age" -lt "$STATUS_COOLDOWN" ]; then
        log "recent rate-limit check ${age}s ago; no-op"
        exit 0
      fi
      ;;
  esac
fi

# --- primary: structured rate-limit API (Issue #195) ----------------------
# Trust the API fully when it answers: rateLimitReachedType != null == limited,
# and the binding window's resetsAt is the reset time. This replaces the tmux
# banner regex as the detector; the regex remains only as the fallback below.
if is_truthy "$API_CHECK" && query_rate_limit_api; then
  printf '%s' "$now" > "$cooldown_file" 2>/dev/null || true
  log "api: reached=${RL_REACHED} type=${RL_REACHED_TYPE:-none} used=${RL_USED_PERCENT:-?}% reset=${RL_RESET_EPOCH:-none} window=${RL_WINDOW_MINS:-?}m plan=${RL_PLAN:-?}"
  if [ "$RL_REACHED" != "1" ]; then
    log "api: not rate-limited; no-op"
    exit 0
  fi
  if api_window_is_long; then
    log "api: limit reached on long/weekly window (${RL_WINDOW_MINS}m > ${MAX_AUTO_WINDOW_MINS}m cap); automatic recovery not attempted"
    exit 0
  fi
  case "$RL_RESET_EPOCH" in
    ''|*[!0-9]*)
      log "api: limit reached but no usable resetsAt; automatic recovery not attempted"
      exit 0
      ;;
  esac
  log "api: rate limit reached (${RL_REACHED_TYPE}); spawning watcher for reset epoch ${RL_RESET_EPOCH}"
  setsid bash "${HOOK_DIR}/codex-rate-limit-watcher.sh" --recover-once-epoch "$PANE" "$RL_RESET_EPOCH" "$RL_WINDOW_MINS" \
    >> "$LOG" 2>&1 < /dev/null &
  exit 0
fi

# --- fallback: legacy pane/status text detection --------------------------
# Reached only when the API could not be queried (codex not on PATH, not logged
# in, app-server error/timeout, or an older Codex without the method).
if is_truthy "$API_CHECK"; then
  log "rate-limit API unavailable; falling back to pane/status text detection"
fi
before="$(pane_tail 80)"
if ! is_truthy "$STATUS_ON_EVERY_STOP" && ! has_rate_limit_text "$payload" "$before"; then
  log "no rate-limit text in Stop payload/pane; no-op"
  exit 0
fi
printf '%s' "$now" > "$cooldown_file" 2>/dev/null || true

status_file="${STATE_DIR}/status.${now}.${pane_key}.txt"
log "rate-limit candidate detected (text fallback); requesting /status"
tmux send-keys -t "$PANE" "/status" 2>>"$LOG" || exit 0
sleep 1
tmux send-keys -t "$PANE" Enter 2>>"$LOG" || exit 0
sleep "$STATUS_WAIT"

{
  printf '%s\n' '--- codex stop payload ---'
  printf '%s\n' "$payload"
  printf '%s\n' '--- codex status capture ---'
  pane_text | tail -n "$STATUS_CAPTURE_LINES"
} > "$status_file" 2>/dev/null || true
log "captured /status output to ${status_file}; spawning one-shot watcher"

setsid bash "${HOOK_DIR}/codex-rate-limit-watcher.sh" --recover-once "$PANE" "$status_file" \
  >> "$LOG" 2>&1 < /dev/null &

exit 0
