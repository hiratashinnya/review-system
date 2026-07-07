#!/usr/bin/env bash
# Start Codex CLI with tmux-based automatic rate-limit recovery.
#
# Usage:
#   tmux new -s codex 'path/to/codex-with-rate-limit-recovery.sh'
#   .codex/hooks/codex-with-rate-limit-recovery.sh --model gpt-5
#
# This wrapper starts the watcher for the current tmux pane, then replaces itself
# with Codex. The watcher observes the pane, waits for a reset when a rate-limit
# banner appears, and submits CODEX_RL_CONTINUE_MSG only when the pane is idle.
set -u

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${CODEX_RL_STATE_DIR:-${HOME}/.codex/rate-limit-recovery}"
mkdir -p "$STATE_DIR" 2>/dev/null || true
LOG="${STATE_DIR}/launcher.log"

log() { printf '%s [launcher] %s\n' "$(date '+%F %T')" "$*" >> "$LOG" 2>/dev/null || true; }

if [ -z "${TMUX:-}" ] || [ -z "${TMUX_PANE:-}" ]; then
  log "not inside tmux; starting codex without recovery watcher"
  exec codex "$@"
fi

setsid bash "${HOOK_DIR}/codex-rate-limit-watcher.sh" "${TMUX_PANE}" \
  >> "${LOG}" 2>&1 < /dev/null &
log "spawned codex-rate-limit-watcher for pane=${TMUX_PANE}"

exec codex "$@"
