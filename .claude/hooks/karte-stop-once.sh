#!/usr/bin/env bash
# Runs the one-shot STOP hook. Any startup or runtime failure is logged to stderr and exits 0.
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 -P -m karte_stop_once.hook "${1:-}" || echo "karte-stop-once: python3 exited with $?" >&2
exit 0
