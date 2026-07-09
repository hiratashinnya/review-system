#!/usr/bin/env bash
# Stop hook handler for Codex CLI rate-limit recovery.
#
# Codex Stop hooks run after a turn stops. When the visible Codex pane looks
# rate-limited, this hook asks the TUI for /status, captures the status text,
# and launches the one-shot watcher to wait until the parsed reset time.
set -u

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

RATE_LIMIT_RE='rate[ -]?limit|usage limit|session limit|request limit|too many requests|hit your .*limit|429.*(rate|limit|too many)|resets?[[:space:]]+([0-9]{1,2}(:[0-9]{2})?[[:space:]]*(am|pm)|mon|tue|wed|thu|fri|sat|sun)'

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

has_rate_limit_text() {
  printf '%s\n%s' "$1" "$2" | grep -qiE "$RATE_LIMIT_RE"
}

payload="$(cat 2>/dev/null || true)"
printf '%s' "$payload" > "$LAST_PAYLOAD" 2>/dev/null || true

if ! is_codex_pane; then
  cur="$(tmux display-message -p -t "$PANE" '#{pane_current_command}' 2>/dev/null || true)"
  path="$(tmux display-message -p -t "$PANE" '#{pane_current_path}' 2>/dev/null || true)"
  log "target pane missing or foreground is not codex/node-wrapper (current='${cur}' path='${path}'); no-op"
  exit 0
fi

before="$(pane_tail 80)"
if ! is_truthy "$STATUS_ON_EVERY_STOP" && ! has_rate_limit_text "$payload" "$before"; then
  log "no rate-limit text in Stop payload/pane; no-op"
  exit 0
fi

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
        log "recent /status request ${age}s ago; no-op"
        exit 0
      fi
      ;;
  esac
fi
printf '%s' "$now" > "$cooldown_file" 2>/dev/null || true

status_file="${STATE_DIR}/status.${now}.${pane_key}.txt"
log "rate-limit candidate detected; requesting /status"
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
