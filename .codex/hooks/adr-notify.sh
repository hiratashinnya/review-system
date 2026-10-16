#!/usr/bin/env bash
# 助言hookは正本checkoutをimportし、読取不能時も操作を継続する。
set -uo pipefail
PROJECT_ROOT="$(git rev-parse --show-toplevel)" || exit 0
cd "$PROJECT_ROOT" || exit 0
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
python3 -m adr.hook
exit 0
