"""Run Git with narrowly scoped subprocess options and fetch environment."""

from __future__ import annotations
import os
import subprocess
from typing import Callable, Mapping, Sequence

def _run_git(
    argv: Sequence[str],
    *,
    cwd,
    runner: Callable[..., subprocess.CompletedProcess],
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """``timeout``/``env`` は明示的に渡されたときだけ ``runner`` へ転送する。

    ネットワーク I/O が起こりうる呼び出し（``git fetch``）だけがこの2つを渡し、それ以外の
    純ローカル操作（``worktree list``/``worktree remove``/``branch -D`` 等）は従来どおり
    渡さない（Issue #426・F-426-05——ハングしうるのは fetch だけなので、対象を広げない）。
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

    ``os.environ`` をコピーした上で ``GIT_TERMINAL_PROMPT=0`` を上書きする——他の環境変数
    （``PATH``/``GIT_SSH`` 等）を握り潰すと fetch 自体が動かなくなる呼び出し環境がありうるため、
    既存 env を丸ごと引き継いだ上でこの1変数だけを足す。
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env
