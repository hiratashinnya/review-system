"""Ledger reads and updates with the original WorktreeError boundary."""

from issue_start.worktree_ledger import LedgerError, add_note, mark, read_ledger
from .worktree_models import WorktreeError

def _entries(repo_root) -> list:
    try:
        return read_ledger(repo_root)["entries"]
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc


def find_entry(repo_root, *, entry_id: str | None = None, worktree_path: str | None = None):
    """``entry_id`` 優先、無ければ ``worktree_path`` で**最新の**エントリを引く。"""
    entries = _entries(repo_root)
    if entry_id is not None:
        for entry in entries:
            if entry.get("entry_id") == entry_id:
                return entry
        return None
    if worktree_path is not None:
        for entry in reversed(entries):
            if entry.get("worktree_path") == worktree_path:
                return entry
    return None


def _mark(repo_root, entry_id: str, status: str, *, now, note: str = "", collected_to=None) -> None:
    try:
        mark(repo_root, entry_id, status, now=now, note=note, collected_to=collected_to)
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc


def _note(repo_root, entry_id: str, *, now, note: str) -> None:
    """状態を変えずに notes へ1行残す（受理した ``--reason`` を落とさないため）。"""
    if not note:
        return
    try:
        add_note(repo_root, entry_id, now=now, note=note)
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc
