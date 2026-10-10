"""Test and finalize only the pending base integration, preserving failure evidence."""

from .base_commit import commit_resolution
from .base_error import require
from .base_journal import finish, reserve
from .base_live import verify_live
from .base_resolution import stage_resolution, validate_pending
from .base_tests import run_tests


def continue_integration(root, entry, binding, operation, modules, api):
    workspace = binding["workspace"]
    before = validate_pending(workspace, operation, binding)
    verify_live(workspace, operation["request"], binding, api)
    reservation = reserve(root, entry, binding, before, action="continue")
    try:
        staged = stage_resolution(workspace, operation, binding)
        tests = run_tests(workspace, modules, staged)
        finish(root, entry["entry_id"], reservation, "testing", release=False,
               tests=tests, tested=staged)
        require(tests["result"] == "pass", "BASE_TEST_FAILED")
        result = commit_resolution(workspace, operation, staged)
        finish(root, entry["entry_id"], reservation, "committed", tests=tests, **result)
        return {"status": "committed", "operation": operation["id"], **result}
    except BaseException as exc:
        finish(root, entry["entry_id"], reservation, "pending", error=str(exc))
        raise
