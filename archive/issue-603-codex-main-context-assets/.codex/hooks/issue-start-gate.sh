#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m issue_start.hook
