"""prompt を shell 文字列へ連結せず、有限時間の子プロセスを実行する。"""

import subprocess

from .results import normalize
from .types import Request, Result
from .version import verified_version


def execute(request: Request, run_id: str):
    try:
        version = verified_version(request)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return Result(run_id, reasons=["agy_version_unverified_or_mismatch"])
    argv = [str(request.executable.resolve()), "--output-format", "json",
            "--print-timeout", f"{request.print_timeout}s"]
    if request.conversation is not None:
        argv.extend(["--conversation", request.conversation])
    argv.extend(["-p", request.prompt])
    try:
        child = subprocess.run(argv, cwd=request.workspace.resolve(), capture_output=True,
                               encoding="utf-8", errors="replace", check=False,
                               timeout=request.print_timeout + 10)
        result = normalize(run_id, child.stdout, child.stderr, child.returncode)
        result.agy_version = version
        return result
    except subprocess.TimeoutExpired as exc:
        stdout = _captured_text(exc.stdout)
        stderr = _captured_text(exc.stderr)
        result = normalize(run_id, stdout, stderr + "\nprint timeout", -1)
        result.agy_version = version
        result.reasons.append("process_timeout")
        return result


def _captured_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""
