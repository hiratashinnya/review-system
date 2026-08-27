#!/usr/bin/env bash
# Codex issue implementer/fixer の全 tool command を durable workspace binding へ再照合する。
set -euo pipefail
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m issue_start.codex_binding hook
