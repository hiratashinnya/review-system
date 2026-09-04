#!/usr/bin/env bash
# SessionStart（matcher: startup|resume）— release_pending の worktree をセッション開始時に
# フル掃除する（Issue #464・F-464-06）。
#
# 毎 dispatch の issue-start-gate（`issue_start.gate._finish_deferred_releases`）は
# `cleanup_branch_ref=False` で `git worktree remove` の再試行だけを行い、`git fetch` を
# 伴うローカルブランチ ref 掃除をホットパスから外している（ネットワーク I/O を毎 dispatch の
# 事前チェックに持ち込まないため）。ここではセッション開始時に1回だけ、削除＋branch ref
# 掃除のフル掃除（`cleanup_branch_ref=True`＝既定）を行う——前セッションのロック保持者 pid は
# 既に死んでいるため、stale ロックが外れて削除が実際に成功しやすい。
#
# best-effort（fail-close の代替ではない）: 失敗しても release_pending のまま持ち越され、
# issue-start-gate の residue/stale 判定・連続失敗の escalation（F-464-02）・次 dispatch の
# deny は従来どおり効く。実体は python 側（`issue_start.session_start`）。
#
# cwd 非依存の起動（F-309-01・共通作法）: 詳細は subagent-karte-inject.sh の同段コメント。
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONSAFEPATH=1
exec python3 -m issue_start.session_start
