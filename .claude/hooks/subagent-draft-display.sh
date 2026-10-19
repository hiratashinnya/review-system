#!/usr/bin/env bash
# SubagentStop（matcher: gh-create-issue）— サブエージェントが tmp/_handoff に書いた
# draft 本文・予定値 preview・完了報告を、AI の要約を経ずに systemMessage でオーナーの
# チャットへ直送する。実体は python 側（`draft_display.stop`）。
#
# 本文を主文脈経由で表示するとサブエージェントの出力＋主文脈の再出力でトークンを二重消費する。
# 停止はブロックしない（可視化専用・fail-open）。診断は stderr（`claude --debug`）。
#
# cwd 非依存の起動（`karte-notify.sh` と同じ作法）: `cd` と `PYTHONSAFEPATH=1` で
# 別ツリーの同名モジュールに覆い隠されないようにする。
set -uo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT" || exit 0
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
python3 -m draft_display stop
exit 0
