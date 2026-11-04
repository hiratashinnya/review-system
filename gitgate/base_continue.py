"""進行中の取り込みを確定する。テストの実行・成功は前提にしない（Issue #706）。"""

from .base_commit import commit_resolution
from .base_live import verify_live
from .base_error import require
from .base_resolution import pending_operation, stage_resolution
from .base_state import clear


def continue_integration(binding, api):
    workspace = binding["workspace"]
    record = pending_operation(workspace, binding["branch"])
    require(isinstance(record.get("base_ref"), str), "BASE_LEGACY_OPERATION_ABORT_REQUIRED")
    verify_live(workspace, record["request"], binding, api, record["base_ref"])
    stage_resolution(workspace, record)
    result = commit_resolution(workspace, record)
    clear(workspace)
    return {"status": "committed", **result}
