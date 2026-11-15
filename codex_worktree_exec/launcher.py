"""`codex exec` を起動し、通常ロールは終了コードをそのまま返す（Issue #538 D9）。

pr-reviewer は異常終了を例外として扱い、終了コード2で返す。

timeout に達したらプロセスグループごと SIGTERM、猶予後に SIGKILL して `CODEX_EXEC_TIMEOUT` で止める。
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Mapping, Sequence

from .child_environment import build_codex_child_environment
from .errors import CodexExecError

TERMINATE_GRACE_SECONDS = 10
STDERR_TAIL_LINES = 6
STDERR_TAIL_CHARS = 1000
ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def _stderr_tail(value: bytes | None) -> str:
    text = (value or b"").decode("utf-8", errors="replace")
    text = ANSI_RE.sub("", text)
    text = "".join(char for char in text if char in "\n\t" or char.isprintable())
    tail = "\n".join(text.splitlines()[-STDERR_TAIL_LINES:])[-STDERR_TAIL_CHARS:]
    return tail.strip()


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
    while time.monotonic() < deadline:
        if not _group_exists(process):
            break
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    else:
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
    quiet: bool = False,
) -> int:
    """通常は出力を透過し、quiet時は保存先ファイルだけを結果に使う。"""
    env = build_codex_child_environment(environ)
    try:
        process = subprocess.Popen(
            list(argv), cwd=str(cwd), env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if quiet else None,
            stderr=subprocess.PIPE if quiet else None,
            start_new_session=True,
        )
    except OSError as error:
        raise CodexExecError("CODEX_EXEC_LAUNCH_FAILED", f"{argv[0]}: {error}") from None
    try:
        outcome = process.communicate(
            input=prompt.encode("utf-8"), timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired:
        _terminate(process)
        raise CodexExecError("CODEX_EXEC_TIMEOUT", f"{timeout_seconds}s") from None
    if quiet and process.returncode:
        detail = f"codex exit={process.returncode}"
        stderr = outcome[1] if isinstance(outcome, tuple) and len(outcome) > 1 else None
        tail = _stderr_tail(stderr)
        if tail:
            detail += f"; stderr tail:\n{tail}"
        raise CodexExecError("CODEX_REVIEW_CODEX_FAILED", detail)
    return process.returncode
