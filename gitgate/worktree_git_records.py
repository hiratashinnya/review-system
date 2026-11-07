"""Inspect linked Git worktrees; do not mutate Git state."""

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Callable
from .worktree_models import WorktreeError
from .worktree_git_runtime import _run_git

def worktree_records(repo_root, *, runner: Callable[..., subprocess.CompletedProcess]) -> list:
    """``git worktree list --porcelain`` を ``{path, branch, locked}`` のレコード列にする。

    **先頭レコードは main worktree（primary checkout）** で、以降が linked worktree
    （porcelain の仕様）。``locked`` は ``locked`` 行（理由付きの ``locked <reason>`` を含む）の
    有無で決める——ハーネスが live な agent worktree をロックする構成では、この印が
    「今まさに動いている dispatch のもの」を示す観測になる（Issue #502）。

    パーサをここ1箇所に集約する（:func:`linked_worktree_paths` も本関数を使う）。同じ
    porcelain を2箇所で別々に読むと、片方だけが ``locked`` を見落とす類のズレが生まれる。
    """
    completed = _run_git(
        ["git", "worktree", "list", "--porcelain"], cwd=repo_root, runner=runner
    )
    if completed.returncode != 0:
        raise WorktreeError("WORKTREE_GIT_ERROR", "worktree list")
    records: list = []
    for line in (completed.stdout or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("worktree "):
            records.append(
                {
                    "path": stripped[len("worktree "):].strip(),
                    "branch": None,
                    "locked": False,
                }
            )
            continue
        if not records:
            continue
        if stripped.startswith("branch "):
            records[-1]["branch"] = stripped[len("branch "):].strip()
        elif stripped == "locked" or stripped.startswith("locked "):
            records[-1]["locked"] = True
    return records


def linked_worktree_paths(repo_root, *, runner: Callable[..., subprocess.CompletedProcess]) -> list:
    """``git worktree list --porcelain`` が返す **linked** worktree の絶対パス一覧。

    porcelain の最初のレコードは main worktree なので除く（main を ``worktree remove`` の
    対象にできないようにする）。
    """
    return [record["path"] for record in worktree_records(repo_root, runner=runner)][1:]


def _is_git_managed(target: Path, repo_root, *, runner) -> bool:
    resolved = target.resolve()
    for candidate in linked_worktree_paths(repo_root, runner=runner):
        try:
            if Path(candidate).resolve() == resolved:
                return True
        except OSError:
            continue
    return False


# --- 台帳参照 ------------------------------------------------------------------
