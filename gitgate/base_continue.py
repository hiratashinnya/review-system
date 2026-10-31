"""進行中の取り込みを確定する。テストの実行・成功は前提にしない（Issue #706）。"""

from .base_commit import commit_resolution
from .base_live import verify_live
from .base_resolution import pending_operation, stage_resolution
from .base_state import clear


def continue_integration(binding, api):
    workspace = binding["workspace"]
    record = pending_operation(workspace, binding["branch"])
    verify_live(workspace, record["request"], binding, api)
    stage_resolution(workspace, record)
    result = commit_resolution(workspace, record)
    clear(workspace)
    return {"status": "committed", **result}
