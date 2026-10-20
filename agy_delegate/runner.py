"""事前検査→排他→直接起動→会話束縛→画像差分回収。自動 retry はない。"""

import os
import uuid
from pathlib import Path

from .artifacts import collect_images, image_snapshot
from .conversation_continuation import mark_continuation_started
from .permissions import inspect_settings
from .process import execute
from .records import check_conversation, execution_lock, save_record, state_root
from .runtime import verify_runtime
from .types import Request, Result
from .workspace_batch import run_parallel, wait_budget as _wait_budget
from .workspace_changes import snapshot, changes, LIMITATIONS


def run(request: Request) -> Result:
    """本番 API は検査注入を受けず、未確認 runtime を停止する。"""
    return _run(request, _wait_budget(request))


def _run(request: Request, wait_seconds: int) -> Result:
    result = Result(uuid.uuid4().hex, workspace_change_limitations=["observation_not_performed"])
    result.reasons = _preflight(request) + verify_runtime(request)
    if result.reasons:
        return result
    try:
        root = state_root(request.workspace.resolve())
        with execution_lock(root, wait_seconds=wait_seconds):
            check_conversation(root, request)
            mark_continuation_started(root, request)
            run_dir = root / result.run_id
            run_dir.mkdir(mode=0o700, exist_ok=False)
            try:
                before = image_snapshot(request.brain, request.conversation) if request.images else {}
                result.workspace_change_limitations = list(LIMITATIONS) + ["observation_incomplete"]
                workspace_before = snapshot(request.workspace)
                try:
                    result = execute(request, result.run_id)
                finally:
                    result.workspace_change_limitations = list(LIMITATIONS) + ["observation_incomplete"]
                    workspace_after = snapshot(request.workspace)
                    result.workspace_changes = changes(workspace_before, workspace_after)
                    result.workspace_change_limitations = list(LIMITATIONS)
                if request.conversation and result.conversation_id != request.conversation:
                    result.reasons.append("conversation_return_mismatch")
                if not request.conversation and (root / f"conversation-{result.conversation_id}.json").exists():
                    result.reasons.append("conversation_id_reused")
                if request.images and result.conversation_id:
                    result.artifacts = collect_images(request.brain, result.conversation_id,
                                                       before, run_dir / "images")
            except (OSError, ValueError) as exc:
                result.reasons.append(str(exc) if isinstance(exc, ValueError) else "execution_io_error")
            if result.reasons and result.classification == "success_candidate":
                result.classification = "failed"
            save_record(root, request, result)
    except (OSError, ValueError) as exc:
        result.reasons.append(str(exc) if isinstance(exc, ValueError) else "execution_io_error")
        result.classification = "failed"
    return result


def _preflight(request: Request) -> list[str]:
    reasons = []
    if request.caller_state != "ready":
        reasons.append("caller_stopped" if request.caller_state == "stopped" else "caller_state_unverified")
    if not request.workspace.is_dir():
        reasons.append("workspace_missing")
    if not request.executable.is_file() or not os.access(request.executable, os.X_OK):
        reasons.append("executable_unavailable")
    if type(request.print_timeout) is not int or not 1 <= request.print_timeout <= 3600:
        reasons.append("print_timeout_invalid")
    if not request.prompt:
        reasons.append("prompt_empty")
    if request.images and (not isinstance(request.brain, Path) or not request.brain.is_dir()):
        reasons.append("brain_unavailable")
    reasons.extend(inspect_settings(request.settings, request.workspace))
    return reasons
