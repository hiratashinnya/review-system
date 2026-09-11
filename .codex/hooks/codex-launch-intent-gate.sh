#!/usr/bin/env bash
set -euo pipefail
COMMON_DIR="$(git rev-parse --path-format=absolute --git-common-dir)"
if [[ "$(basename "$COMMON_DIR")" != ".git" ]]; then
  echo 'CODEX_LAUNCH_CONTROL_ROOT_INVALID' >&2
  exit 2
fi
PROJECT_ROOT="$(dirname "$COMMON_DIR")"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m issue_start.codex_launch_intent hook
