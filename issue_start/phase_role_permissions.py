"""新工程のコマンド権限を PF hook に接続する。"""
from .gated_roles import GATED_ROLES, WRITE_ROLES


def extend_phase_permissions(gitgate, github, feedback=None):
    """既存3ロールの権限を変えず、新工程へ最小権限を追加する。"""
    for role in GATED_ROLES - {"issue-implementer", "issue-fixer", "pr-reviewer"}:
        gitgate[role] = {"diff", "log", "show-pr-diff"}
        if role in WRITE_ROLES:
            gitgate[role] |= {
                "status", "add", "commit", "push", "branch-current", "new-branch", "adopt-branch", "fetch",
            }
        github[role] = {("pr", "list"), ("pr", "view"), ("issue", "view")}
        if feedback is not None:
            feedback[role] = {"check", "status", "index"}
