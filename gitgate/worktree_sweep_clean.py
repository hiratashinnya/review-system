"""Fail-closed worktree cleanliness and cross-pane lock observations."""

from pathlib import Path
from .worktree_models import WorktreeError
from .worktree_path_validation import resolve_within
from .worktree_git_runtime import _run_git
from .worktree_git_records import worktree_records

def _is_worktree_clean(repo_root, entry, *, runner) -> tuple:
    """作業ツリーに未コミット/未追跡の変更が無いことを確認する（Issue #502・F-502-01）。

    返り値は ``(bool, 理由)``。真を返すのは ``git status --porcelain`` を実際に実行できて、
    その出力が空だったときだけ——**判定できなかったときは偽**（fail-close）。
    「見られなかった」を「捨ててよい」に潰さない。

    **この関門は handoff の有無で免除しない**。実体を消す :func:`_remove_worktree_dir` は
    ``git worktree remove --force`` を使い、dirty / untracked を問答無用で消す。handoff を
    書き終えていることは「作業ツリーに未コミットの何かが残っていない」ことを含意しないため、
    handoff がある経路（:func:`_sweep_one` の ``how == "unique"``）でも回収の**後で**必ず通す。
    """
    relative = entry.get("worktree_path")
    try:
        target = resolve_within(repo_root, relative)
    except WorktreeError as exc:
        return False, f"worktree のパスを解決できない（{exc.reason}）"
    if not target.is_dir():
        return False, "worktree の実体が無い"
    status = _run_git(["git", "status", "--porcelain"], cwd=target, runner=runner)
    if status.returncode != 0:
        return False, "git status を実行できない（判定不能）"
    if (status.stdout or "").strip():
        return False, "作業ツリーに未コミット/未追跡の変更がある"
    return True, ""

def _locked_worktree_paths(repo_root, *, runner) -> set:
    """``locked`` と報告された worktree の解決済み絶対パス集合。"""
    locked = set()
    for record in worktree_records(repo_root, runner=runner):
        if not record.get("locked"):
            continue
        try:
            locked.add(str(Path(record["path"]).resolve()))
        except OSError:
            continue
    return locked
