"""新工程のコマンド権限を PF hook に接続する。"""
from .gated_roles import GATED_ROLES, WRITE_ROLES


def extend_phase_permissions(gitgate, github, feedback=None):
    """既存権限を保持し、2bを含む新工程へ必要なverbだけ追加する。"""
    gitgate["issue-implementer"].add("adopt-branch")
    for role in GATED_ROLES - {"issue-implementer", "issue-fixer", "pr-reviewer"}:
        gitgate[role] = {"diff", "log", "show-pr-diff"}
        if role in WRITE_ROLES:
            gitgate[role] |= {
                "status", "add", "commit", "push", "branch-current", "new-branch", "adopt-branch", "fetch",
            }
        github[role] = {("pr", "list"), ("pr", "view"), ("issue", "view")}
        if feedback is not None:
            feedback[role] = {"check", "status", "index"}
