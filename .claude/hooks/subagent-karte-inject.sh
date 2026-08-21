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
#
# cwd 非依存の起動（F-309-01）: `python3 -m` は **sys.path[0] にプロセスの cwd を先に置く**
# ため、PYTHONPATH に $CLAUDE_PROJECT_DIR を入れるだけでは足りない——別ツリー（linked
# worktree・別 checkout）を cwd にして起動されると、cwd 側の `issue_start` が
# $CLAUDE_PROJECT_DIR 側の実体を覆い隠し ModuleNotFoundError で exit 1 になる。
# 二重に閉じる:
#   * `cd "$PROJECT_ROOT"` … cwd 自体を正本側へ寄せる（python の版に依存しない）。
#   * `PYTHONSAFEPATH=1` … cwd の暗黙追加そのものを止める（3.11+。旧版では無視される）。
# どちらか一方でも成立すれば正本側の実体に届く。
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
exec python3 -m issue_start.subagent_hooks karte-inject
