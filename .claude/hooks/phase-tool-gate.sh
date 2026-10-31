#!/usr/bin/env bash
# PreToolUse(Write|Edit|NotebookEdit) の read-only 工程 gate。`issue-start-gate.sh` と同形（#685 F-685-33）。
# `-P` で cwd を sys.path に入れず、gate のコードは信頼側（$CLAUDE_PROJECT_DIR か本スクリプトの root）から読む。
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -P -m issue_start.phase_tool_gate
