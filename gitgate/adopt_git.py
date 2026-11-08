"""Shared bounded git runner and success/error contract."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Callable, Mapping, Sequence
from branch_source.policy import BranchSourceError
def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess],
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """``timeout``/``env`` は明示的に渡されたときだけ ``runner`` へ転送する。

    ネットワーク I/O が起こりうる呼び出し（stage 1 の ``git fetch``）だけがこの2つを渡し、
    それ以外の純ローカル操作（``rev-parse``/``switch``/``branch`` 等）は従来どおり渡さない
    （Issue #426・F-426-05——ハングしうるのは fetch だけなので、対象を広げない）。
    """
    kwargs: dict = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if env is not None:
        kwargs["env"] = env
    return runner(
        list(argv), cwd=str(cwd), text=True, capture_output=True, shell=False, **kwargs
    )


def _fetch_env() -> dict:
    """``git fetch`` を非対話化する env（stdin 経由の認証プロンプト待ちでハングしないため）。

    ``worktree.py::_fetch_env`` と同じ考え方——``os.environ`` を丸ごと引き継いだ上で
    ``GIT_TERMINAL_PROMPT=0`` だけを上書きする（他の env を握り潰さない）。
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _require_ok(
    completed: subprocess.CompletedProcess, reason: str, detail: str = ""
) -> str:
    if completed.returncode != 0:
        raise BranchSourceError(reason, detail)
    return (completed.stdout or "").strip()
