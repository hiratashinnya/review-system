"""`-C` が呼び出し元自身の linked worktree であることを確かめる（Issue #538 D5）。

登録済み linked worktree の列挙は `gitgate.worktree.linked_worktree_paths` を再利用する。
main worktree（primary checkout）はこの列挙に入らないため、`-C` に指定できない。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from gitgate.worktree import WorktreeError, linked_worktree_paths

from .errors import CodexExecError

Runner = Callable[..., subprocess.CompletedProcess]


def _toplevel(cwd: Path, runner: Runner) -> Path:
    completed = runner(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, shell=False, check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise CodexExecError("CODEX_EXEC_CWD_NOT_IN_REPOSITORY", str(cwd))
    return Path(completed.stdout.strip()).resolve()


def _registered(toplevel: Path, runner: Runner) -> set[Path]:
    try:
        candidates = linked_worktree_paths(toplevel, runner=runner)
    except WorktreeError as error:
        raise CodexExecError("CODEX_EXEC_GIT_FAILED", str(error)) from None
    registered = set()
    for candidate in candidates:
        try:
            registered.add(Path(candidate).resolve(strict=True))
        except OSError:
            continue
    return registered


def bind_worktree(requested: Path, cwd: Path, *, runner: Runner = subprocess.run) -> Path:
    """検査に通った worktree の実パスを返す。相対パスは `cwd` 基準で解決する。"""
    try:
        target = (cwd / requested).resolve(strict=True)
    except OSError:
        raise CodexExecError("CODEX_EXEC_WORKTREE_MISSING", str(requested)) from None
    toplevel = _toplevel(cwd, runner)
    if target != toplevel:
        raise CodexExecError(
            "CODEX_EXEC_WORKTREE_CWD_MISMATCH", f"-C {target} != cwd toplevel {toplevel}"
        )
    if target not in _registered(toplevel, runner):
        raise CodexExecError("CODEX_EXEC_WORKTREE_UNREGISTERED", str(target))
    return target
