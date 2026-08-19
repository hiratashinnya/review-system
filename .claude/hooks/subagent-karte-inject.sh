#!/usr/bin/env bash
# SubagentStart（matcher: issue-fixer）— カルテ手順の注入（Issue #309・PR-1）。
#
# 実体は python 側（`issue_start.subagent_hooks karte-inject`）。`issue-start-gate.sh` と
# 同じ「薄い起動口 + python モジュール」構成にしてあるのは、判定ロジックを
# `tests/unit/test_subagent_hooks.py` から**サブプロセスを介さず**直接呼べるようにするため
# （フック本体をシェルの heredoc に埋めると、注入点（repo_root / now / runner）を持てず
# 実リポジトリを汚さずに検証できない）。
#
# 失敗時: 何も注入せず exit 0（注入は助言＝fail-open）。
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m issue_start.subagent_hooks karte-inject
