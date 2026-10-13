"""事前検査→排他→直接起動→会話束縛→画像差分回収。自動 retry はない。"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .artifacts import collect_images, image_snapshot
from .permissions import inspect_settings
from .process import execute
from .records import check_conversation, execution_lock, save_record, state_root
from .runtime import verify_runtime
from .types import Request, Result


def run(request: Request) -> Result:
    """本番 API は検査注入を受けず、未確認 runtime を停止する。"""
    result = Result(uuid.uuid4().hex)
    result.reasons = _preflight(request) + verify_runtime(request)
    if result.reasons:
        return result
    root = None
    try:
        root = state_root(request.workspace.resolve())
        with execution_lock(root):
            check_conversation(root, request)
            run_dir = root / result.run_id
            run_dir.mkdir(mode=0o700, exist_ok=False)
            try:
                before = image_snapshot(request.brain, request.conversation) if request.images else {}
                result = execute(request, result.run_id)
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


def run_parallel(requests: list[Request], *, max_concurrency: int,
                 ) -> list[Result]:
    """結果順は入力順。1件失敗を全体成功へ集約しない。"""
    if not 1 <= max_concurrency <= 8:
        raise ValueError("parallel_limit_invalid")
    with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
        futures = [pool.submit(run, request) for request in requests]
        return [future.result() for future in futures]


def _preflight(request: Request) -> list[str]:
    reasons = []
    if request.caller_state != "ready":
        reasons.append("caller_stopped" if request.caller_state == "stopped" else "caller_state_unverified")
    if not request.workspace.is_dir():
        reasons.append("workspace_missing")
    if not request.executable.is_file() or not os.access(request.executable, os.X_OK):
        reasons.append("executable_unavailable")
    if isinstance(request.print_timeout, bool) or not 1 <= request.print_timeout <= 3600:
        reasons.append("print_timeout_invalid")
    if not request.prompt:
        reasons.append("prompt_empty")
    if request.images and (not isinstance(request.brain, Path) or not request.brain.is_dir()):
        reasons.append("brain_unavailable")
    reasons.extend(inspect_settings(request.settings, request.workspace))
    return reasons
