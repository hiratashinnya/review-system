#!/usr/bin/env bash
# SubagentStop（matcher: issue-implementer|issue-fixer）— カルテ未更新の停止を拒否し、
# 終了した dispatch の worktree を回収してから解放する（Issue #309・PR-1 ＋ Issue #354・PR-3）。
#
# 実体は python 側（`issue_start.subagent_hooks stop`）。段は逐次で、前段が block したら
# 後段へ進まない:
#   1. `issue-fixer` は `tmp/_karte/active.json` の {issue, round} で `karte check` を実行し、
#      非0 または判定不能なら `{"decision":"block","reason":...}` を stdout・**exit 0** で返す。
#   2. 回収・解放段: 台帳を running → stopped へ進めてから
#      `python3 -m gitgate collect-worktree` を起動する（回収→検証→解放の1操作）。
#      失敗したら削除せず stale へ落として exit 0（次 dispatch の gate deny が拾う）。
#
# **2 を別フックに分けないのは意図的**。同一イベントに「ブロックするフック」と
# 「削除するフック」を別々に登録すると、ブロックされて継続したエージェントの worktree を
# 別フックが消す致命的な競合が起きるため。単一スクリプトの逐次段なら
# 「block したら解放段へ進まない」が構造的に保証される。
#
# このスクリプトも python 側も `git worktree remove` を直接呼ばない——実体を消してよいかの
# 判断は `gitgate/worktree.py` に集約されている。
#
# cwd 非依存の起動（F-309-01・共通作法）: 詳細は subagent-karte-inject.sh の同段コメント。
# ここが破れると「fail-close であるべき停止ゲートが ModuleNotFoundError で exit 1 になり
# block されずに素通りする」＝統制が黙って無効化される。
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
exec python3 -m issue_start.subagent_hooks stop
