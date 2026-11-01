"""排他待機後と版照会後にcohortを再照合し、通常promptだけを起動する。"""

import subprocess

from . import process
from .types import Request, Result


def execute_verified(request: Request, run_id: str) -> Result:
    """通常APIに任意checkerを受けず、校正低層入口と区別する。"""
    from .runner import verify_runtime
    reasons = verify_runtime(request)
    if reasons:
        return Result(run_id, reasons=reasons)
    try:
        version = process.verified_version(request)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return Result(run_id, reasons=["agy_version_unverified_or_mismatch"])
    reasons = verify_runtime(request)
    if reasons:
        return Result(run_id, agy_version=version, reasons=reasons)
    return process._execute_prompt(request, run_id, version)
