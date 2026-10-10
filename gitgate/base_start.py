"""Begin a fixed, uncommitted two-parent integration after live evidence checks."""

from .base_error import require
from .base_git import foreign_operation, git, merge_head
from .base_journal import active_operation, finish, reserve
from .base_live import verify_live
from .base_protection import reject_protected_incoming
from .base_snapshot import conflict_paths, snapshot


def start(root, entry, binding, request, api):
    workspace = binding["workspace"]
    before = snapshot(workspace)
    require(active_operation(entry) is None, "BASE_OPERATION_PENDING")
    require(not before["status"] and not before["merge_head"]
            and not foreign_operation(workspace), "BASE_WORKTREE_NOT_CLEAN")
    require(before["head"] == request["head"], "BASE_HEAD_OID_MISMATCH")
    verify_live(workspace, request, binding, api)
    reject_protected_incoming(workspace, request["head"], request["base"])
    require(snapshot(workspace) == before, "BASE_CONTENT_CAS_MISMATCH")
    operation = reserve(root, entry, binding, before, request=request)
    if git(workspace, "merge-base", "--is-ancestor", request["base"], request["head"],
           allow_failure=True).returncode == 0:
        finish(root, entry["entry_id"], operation, "no_change", after=before)
        return {"status": "no_change", "operation": operation["id"]}
    result = git(workspace, "merge", "--no-ff", "--no-commit", request["base"],
                 allow_failure=True)
    after = snapshot(workspace)
    require(after["head"] == before["head"] and merge_head(workspace) == request["base"],
            "BASE_START_MERGE_STATE_INVALID")
    conflicts = conflict_paths(after["index"])
    require(result.returncode == 0 or result.returncode == 1 and conflicts,
            "BASE_START_FAILED")
    finish(root, entry["entry_id"], operation, "pending", merge_snapshot=after,
           conflicts=conflicts)
    return {"status": "conflicts" if conflicts else "ready", "conflicts": conflicts,
            "operation": operation["id"]}
