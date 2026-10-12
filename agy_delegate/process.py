"""prompt を shell 文字列へ連結せず、有限時間の子プロセスを実行する。"""

import subprocess

from .results import normalize
from .types import Request


def execute(request: Request, run_id: str):
    argv = [str(request.executable.resolve()), "--output-format", "json",
            "--print-timeout", str(request.print_timeout)]
    if request.conversation is not None:
        argv.extend(["--conversation", request.conversation])
    argv.extend(["-p", request.prompt])
    try:
        child = subprocess.run(argv, cwd=request.workspace.resolve(), capture_output=True,
                               encoding="utf-8", errors="replace", check=False,
                               timeout=request.print_timeout + 10)
        return normalize(run_id, child.stdout, child.stderr, child.returncode)
    except subprocess.TimeoutExpired as exc:
        stdout = _captured_text(exc.stdout)
        stderr = _captured_text(exc.stderr)
        result = normalize(run_id, stdout, stderr + "\nprint timeout", -1)
        result.reasons.append("process_timeout")
        return result


def _captured_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""
