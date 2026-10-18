"""git index から staged path と file bytes を読む。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Sequence


def _run_git(
    argv: Sequence[str],
    *,
    root: Path,
    runner: Callable[..., subprocess.CompletedProcess],
    text: bool,
) -> subprocess.CompletedProcess:
    return runner(
        list(argv), cwd=str(root), capture_output=True, text=text, shell=False, check=False
    )


def _staged_paths(
    root: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess],
) -> set[str]:
    completed = _run_git(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD", "-z"],
        root=root,
        runner=runner,
        text=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"staged path の取得に失敗しました: {detail}")
    return {
        item.decode("utf-8")
        for item in (completed.stdout or b"").split(b"\0")
        if item
    }


def _index_loader(
    root: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess],
) -> Callable[[str], bytes]:
    def load(relative: str) -> bytes:
        completed = _run_git(
            ["git", "show", f":{relative}"],
            root=root,
            runner=runner,
            text=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"index の {relative} を読めません: {detail}")
        return completed.stdout or b""

    return load
