#!/usr/bin/env bash
# SubagentStop（matcher: issue-implementer|issue-fixer）— カルテ未更新の停止を拒否する
# （Issue #309・PR-1）。
#
# 実体は python 側（`issue_start.subagent_hooks stop`）。
#   * `issue-fixer` は `tmp/_karte/active.json` の {issue, round} で `karte check` を実行し、
#     非0 または判定不能なら `{"decision":"block","reason":...}` を stdout・**exit 0** で返す。
#   * **PR-3 で回収・解放段をこの同じスクリプトへ足す**（別フックに分けない）。同一イベントに
#     「ブロックするフック」と「削除するフック」を別々に登録すると、ブロックされて継続した
#     エージェントの worktree を別フックが消す致命的な競合が起きるため。
#
# 本 PR は worktree を1つも削除しない（`git worktree remove` を呼ぶコードが存在しない）。
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
