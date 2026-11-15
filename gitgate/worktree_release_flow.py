"""Ledger-state-gated release operation; do not remove live or uncollected work."""

import subprocess
from typing import Callable
from .worktree_models import WorktreeError, ReleaseOutcome
from .worktree_arg_common import _validate_entry_id, _validate_reason
from .worktree_path_validation import validate_worktree_path
from .worktree_ledger_access import find_entry, _mark, _note
from .worktree_release_safety import _reason_note, _remove_worktree_dir
from .worktree_branch_cleanup import _cleanup_branch_ref

def worktree_release(
    repo_root,
    worktree_path: str,
    *,
    entry_id: str | None = None,
    force_uncollected: bool = False,
    reason: str = "",
    now,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    cleanup_branch_ref: bool = True,
) -> ReleaseOutcome:
    """Remove an eligible linked worktree, then optionally clean its local ref."""
    relative = validate_worktree_path(worktree_path)
    if entry_id is not None:
        _validate_entry_id(entry_id)
    if force_uncollected or reason:
        _validate_reason(reason)

    entry = find_entry(repo_root, entry_id=entry_id, worktree_path=relative)
    if entry_id is not None and entry is None:
        raise WorktreeError("WORKTREE_ENTRY_NOT_FOUND", entry_id)
    if entry is not None:
        bound = entry.get("worktree_path")
        if bound is not None and bound != relative:
            raise WorktreeError(
                "WORKTREE_ENTRY_PATH_MISMATCH", f"entry={bound}; argument={relative}"
            )

    status = entry.get("status") if entry is not None else None
    resolved_entry_id = entry.get("entry_id") if entry is not None else None
    note = _reason_note(
        "worktree-release",
        reason,
        flag="--force-uncollected" if force_uncollected else "",
    )

    if status in ("released", "abandoned"):
        removed = _remove_worktree_dir(repo_root, relative, runner=runner)
        if resolved_entry_id is not None:
            if removed:
                _note(
                    repo_root,
                    resolved_entry_id,
                    now=now,
                    note=f"worktree-release: 終端状態（{status}）の残留実体を削除した",
                )
                if cleanup_branch_ref:
                    _cleanup_branch_ref(repo_root, entry, now=now, runner=runner)
            _note(repo_root, resolved_entry_id, now=now, note=note)
        return ReleaseOutcome(relative, resolved_entry_id, removed=removed, status=status)

    if status == "running":
        raise WorktreeError(
            "WORKTREE_LIVE",
            f"{relative}（live な dispatch が所有している。--force-uncollected でも解放しない）",
        )
    if status == "open":
        raise WorktreeError(
            "WORKTREE_NOT_BOUND",
            f"{relative}（worktree がまだ束縛されていない＝解放対象を特定できない）",
        )
    if status == "stopped":
        raise WorktreeError(
            "WORKTREE_NOT_COLLECTED",
            f"{relative}（所有者は停止したがまだ回収していない。collect-worktree で回収する"
            "＝--force-uncollected では上書きしない）",
        )
    if status == "stale" and not force_uncollected:
        raise WorktreeError(
            "WORKTREE_NOT_COLLECTED",
            f"{relative}（回収されていない。--force-uncollected --reason <text> が要る）",
        )
    if entry is None and not force_uncollected:
        raise WorktreeError(
            "WORKTREE_ORPHAN_REQUIRES_FORCE",
            f"{relative}（台帳にエントリが無い。--force-uncollected --reason <text> が要る）",
        )

    removed = _remove_worktree_dir(repo_root, relative, runner=runner)
    if resolved_entry_id is not None:
        _mark(repo_root, resolved_entry_id, "released", now=now, note=note)
        if removed and cleanup_branch_ref:
            _cleanup_branch_ref(repo_root, entry, now=now, runner=runner)
    return ReleaseOutcome(relative, resolved_entry_id, removed=removed, status="released")
