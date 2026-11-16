"""Resolve the collect target and reject unsafe ledger states before any I/O."""

from .worktree_models import WorktreeError
from .worktree_arg_common import _validate_entry_id, _validate_reason
from .worktree_path_validation import validate_worktree_path
from .worktree_ledger_access import find_entry

def select_collect_target(repo_root, *, entry_id, worktree_path, allow_missing_handoff, reason):
    if entry_id is not None:
        _validate_entry_id(entry_id)
    if allow_missing_handoff or reason:
        _validate_reason(reason)

    entry = None
    if entry_id is not None:
        entry = find_entry(repo_root, entry_id=entry_id)
        if entry is None:
            raise WorktreeError("WORKTREE_ENTRY_NOT_FOUND", entry_id)

    relative_worktree = worktree_path
    if relative_worktree is None and entry is not None:
        relative_worktree = entry.get("worktree_path")
    if not relative_worktree:
        raise WorktreeError(
            "COLLECT_WORKTREE_UNKNOWN",
            f"{entry_id}（台帳の worktree_path が未束縛。<worktree-path> を明示する）",
        )
    relative_worktree = validate_worktree_path(relative_worktree)
    if entry is not None:
        bound = entry.get("worktree_path")
        if bound is not None and bound != relative_worktree:
            raise WorktreeError(
                "WORKTREE_ENTRY_PATH_MISMATCH", f"entry={bound}; argument={relative_worktree}"
            )
    if entry is None:
        entry = find_entry(repo_root, worktree_path=relative_worktree)

    status = entry.get("status") if entry is not None else None
    if status not in ("released", "abandoned"):
        if status == "running":
            raise WorktreeError(
                "WORKTREE_LIVE",
                f"{relative_worktree}（live な dispatch が所有している。停止してから回収する）",
            )
        if status == "open":
            raise WorktreeError("WORKTREE_NOT_BOUND", relative_worktree)
    return entry, relative_worktree, status
