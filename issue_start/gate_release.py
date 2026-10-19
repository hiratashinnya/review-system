"""Retry deferred worktree releases recorded by the Issue-start ledger."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping

from . import worktree_ledger

DEFERRED_RELEASE_FAILURE_MARKER = "DEFERRED_RELEASE_RETRY_FAILED"
DEFERRED_RELEASE_FAILURE_THRESHOLD = 3


def _deferred_release_failure_count(entry: Mapping[str, Any]) -> int:
    notes = entry.get("notes")
    if not isinstance(notes, list):
        return 0
    return sum(
        1
        for item in notes
        if isinstance(item, Mapping)
        and DEFERRED_RELEASE_FAILURE_MARKER in str(item.get("note", ""))
    )


def _record_release_failure(
    root: Path, entry: Mapping[str, Any], entry_id: str, reason: str, now: datetime
) -> dict[str, Any]:
    failure_count = _deferred_release_failure_count(entry) + 1
    if failure_count > DEFERRED_RELEASE_FAILURE_THRESHOLD:
        try:
            worktree_ledger.mark(
                root, entry_id, "stale", now=now,
                note=(
                    "issue-start-gate: release_pending の削除が"
                    f"{failure_count}回連続で失敗したため stale へ落とした"
                    f"（Issue #464・{DEFERRED_RELEASE_FAILURE_MARKER}・{reason}）"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - keep dispatch moving if logging fails
            return {
                "entry_id": entry_id, "released": False, "error": reason,
                "escalate_error": type(exc).__name__,
            }
        return {
            "entry_id": entry_id, "released": False, "error": reason,
            "escalated_to_stale": True,
        }
    try:
        worktree_ledger.add_note(
            root, entry_id, now=now,
            note=(
                "issue-start-gate: release_pending の削除リトライに失敗した"
                f"（{failure_count}回目・{DEFERRED_RELEASE_FAILURE_MARKER}・{reason}）"
            ),
        )
    except Exception:  # noqa: BLE001 - preserve the original fail-open cleanup behavior
        pass
    return {"entry_id": entry_id, "released": False, "error": reason}


def _finish_deferred_release(
    root: Path,
    entry: Mapping[str, Any],
    *,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any] | None:
    from gitgate.worktree import WorktreeError, worktree_release

    entry_id = entry.get("entry_id")
    worktree_path = entry.get("worktree_path")
    if not isinstance(entry_id, str) or not isinstance(worktree_path, str) or not worktree_path:
        return None
    try:
        outcome = worktree_release(
            root, worktree_path, entry_id=entry_id,
            reason="issue-start-gate: 遅延していた解放を完了した（Issue #464）",
            now=now, runner=runner, cleanup_branch_ref=False,
        )
    except Exception as exc:  # noqa: BLE001 - failed cleanup is retried on the next dispatch
        reason = exc.reason if isinstance(exc, WorktreeError) else type(exc).__name__
        return _record_release_failure(root, entry, entry_id, reason, now)
    return {"entry_id": entry_id, "released": outcome.status == "released"}


def _finish_deferred_releases(
    root: Path,
    *,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> list[dict[str, Any]]:
    finished = []
    for entry in worktree_ledger.deferred_release_entries(root):
        result = _finish_deferred_release(root, entry, now=now, runner=runner)
        if result is not None:
            finished.append(result)
    return finished
