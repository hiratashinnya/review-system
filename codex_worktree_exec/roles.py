"""Codex 実行者経路を使えるロールの集合（Issue #538 D4）。

`issue_start.gated_roles.GATED_ROLES` から読取専用の `pr-reviewer` を除いて導出し、
書込ロール名をリテラルで再定義しない。`.claude/hooks/agent-command-gate.sh` もこの値を読む。
"""

from __future__ import annotations

from issue_start.gated_roles import GATED_ROLES

READ_ONLY_ROLE = "pr-reviewer"
CODEX_EXEC_ROLES = GATED_ROLES - frozenset({READ_ONLY_ROLE})

__all__ = ["CODEX_EXEC_ROLES", "READ_ONLY_ROLE"]
