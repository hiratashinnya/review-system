#!/usr/bin/env bash
# PreToolUse(Write|Edit) — gh-create-issue must not forge SubagentStop receipts.
set -uo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT" || exit 0
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
python3 -m draft_display.receipt_gate
exit 0
