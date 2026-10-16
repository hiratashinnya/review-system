#!/usr/bin/env bash
# ADR 書込直後の pending 通知。判定は共有 Python 実装で行う。
set -uo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT" || exit 0
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
python3 -m adr.hook
exit 0
