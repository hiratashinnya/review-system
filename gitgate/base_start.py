"""PR base を head checkout へ未確定の2親 merge として取り込み始める。"""

from .base_error import BaseIntegrationError, require
from .base_git import foreign_operation, git, merge_head, output, is_clean, unmerged_paths
from .base_live import verify_live
from .base_state import clear, create, load, update


def require_clean_start(workspace, request):
    require(load(workspace) is None, "BASE_OPERATION_PENDING")
    require(is_clean(workspace) and merge_head(workspace) is None
            and not foreign_operation(workspace), "BASE_WORKTREE_NOT_CLEAN")
    require(output(workspace, "rev-parse", "HEAD") == request["head"], "BASE_HEAD_OID_MISMATCH")


def start(binding, request, api):
    workspace = binding["workspace"]
    require_clean_start(workspace, request)
    verify_live(workspace, request, binding, api)
    require_clean_start(workspace, request)
    if git(workspace, "merge-base", "--is-ancestor", request["base"], request["head"],
           allow_failure=True).returncode == 0:
        return {"status": "no_change", "head": request["head"]}
    record = {"request": request, "branch": binding["branch"],
              "original_head": request["head"], "conflicts": []}
    create(workspace, record)
    result = git(workspace, "merge", "--no-ff", "--no-commit", request["base"],
                 allow_failure=True)
    if merge_head(workspace) is None and output(workspace, "rev-parse", "HEAD") == request["head"]:
        clear(workspace)
        raise BaseIntegrationError(
            "BASE_START_FAILED: " + result.stderr.decode(errors="replace").strip())
    require(output(workspace, "rev-parse", "HEAD") == request["head"]
            and merge_head(workspace) == request["base"], "BASE_START_MERGE_STATE_INVALID")
    record["conflicts"] = unmerged_paths(workspace)
    require(result.returncode == 0 or record["conflicts"], "BASE_START_FAILED")
    update(workspace, record)
    return {"status": "conflicts" if record["conflicts"] else "ready",
            "conflicts": record["conflicts"]}
