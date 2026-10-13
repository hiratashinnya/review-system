"""`codex exec` を起動し、終了コードをそのまま返す（Issue #538 D9）。

timeout に達したらプロセスグループごと SIGTERM、猶予後に SIGKILL して `CODEX_EXEC_TIMEOUT` で止める。
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Mapping, Sequence

from .errors import CodexExecError
from .nesting_guard import NESTING_MARKER

TERMINATE_GRACE_SECONDS = 10


def _signal_group(process: subprocess.Popen, signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def _terminate(process: subprocess.Popen) -> None:
    _signal_group(process, signal.SIGTERM)
    deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    while time.monotonic() < deadline and _group_exists(process):
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    if _group_exists(process):
        _signal_group(process, signal.SIGKILL)
    process.wait()


def _group_exists(process: subprocess.Popen) -> bool:
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    return True


def run_codex(
    argv: Sequence[str],
    prompt: str,
    *,
    cwd: Path,
    timeout_seconds: int,
    environ: Mapping[str, str],
) -> int:
    """stdout/stderr は呼び出し元へ透過し、依頼文だけを stdin へ流す。"""
    env = {**environ, NESTING_MARKER: "1"}
    try:
        process = subprocess.Popen(
            list(argv), cwd=str(cwd), env=env, stdin=subprocess.PIPE, start_new_session=True,
        )
    except OSError as error:
        raise CodexExecError("CODEX_EXEC_LAUNCH_FAILED", f"{argv[0]}: {error}") from None
    try:
        process.communicate(input=prompt.encode("utf-8"), timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate(process)
        raise CodexExecError("CODEX_EXEC_TIMEOUT", f"{timeout_seconds}s") from None
    return process.returncode
