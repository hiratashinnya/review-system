"""委譲先でも元ロールの権限を維持するロール集合。"""
from issue_start.gated_roles import GATED_ROLES, READ_ONLY_ROLES, WRITE_ROLES

READ_ONLY_ROLE = "pr-reviewer"
CODEX_EXEC_ROLES = GATED_ROLES
NEW_EXEC_ROLES = GATED_ROLES - {"issue-implementer", "issue-fixer"}

__all__ = ["CODEX_EXEC_ROLES", "READ_ONLY_ROLE", "READ_ONLY_ROLES", "WRITE_ROLES"]
