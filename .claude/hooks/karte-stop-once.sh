#!/usr/bin/env bash
# Issue #513 trial. PostToolUse arms an issue-scoped event for this session only.
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -P -m karte_stop_once.hook "$1"
