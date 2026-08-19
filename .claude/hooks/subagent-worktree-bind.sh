#!/usr/bin/env bash
# SubagentStart（matcher: issue-implementer|issue-fixer）— worktree 所有台帳への束縛
# （Issue #309・PR-1）。
#
# 実体は python 側（`issue_start.subagent_hooks bind`）。起動した dispatch の
# `.claude/worktrees/agent-<id>` を台帳の `open` エントリへ結び付け `running` にする。
# **worktree を1つも削除しない**（削除経路は本 PR に存在しない）。
#
# 出力は常に無出力 exit 0（本 PR では何も止めない）。evidence は stderr（`claude --debug`）。
#
# cwd 非依存の起動（F-309-01・共通作法）: 詳細は subagent-karte-inject.sh の同段コメント。
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
exec python3 -m issue_start.subagent_hooks bind
