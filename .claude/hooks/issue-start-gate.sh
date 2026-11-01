#!/usr/bin/env bash
# PreToolUse(Task|Agent) の dispatch gate。cwd は検査作業面なので cd しない（#685 F-685-22）。
# `-P` で cwd を sys.path に入れず、gate のコードは信頼側（$CLAUDE_PROJECT_DIR か本スクリプトの root）から読む。
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -P -m issue_start.hook
