"""Ordered collect pipeline: target -> handoff -> ledger -> release."""

from issue_start.worktree_ledger import DEFERRED_RELEASE_STATUS
from .worktree_models import CollectOutcome
from .worktree_collect_target import select_collect_target
from .worktree_collect_handoff import collect_handoff
from .worktree_collect_finish import finish_collect
from .worktree_ledger_access import _mark, _note
from .worktree_release_safety import _reason_note

def collect_worktree_flow(repo_root, *, entry_id, worktree_path, handoff_path,
                          into, allow_missing_handoff, reason, now, runner,
                          max_bytes, release, read_handoff, write_collected, release_fn):
    entry, relative_worktree, status = select_collect_target(
        repo_root, entry_id=entry_id, worktree_path=worktree_path,
        allow_missing_handoff=allow_missing_handoff, reason=reason,
    )
    if status in ("released", "abandoned"):
        return CollectOutcome(
            relative_worktree, entry.get("entry_id"), entry.get("collected_to"), released=False
        )

    resolved_entry_id = entry.get("entry_id") if entry is not None else None
    collected_to = entry.get("collected_to") if entry is not None else None
    reason_recorded = False
    if status not in ("collected", DEFERRED_RELEASE_STATUS):
        collected_to, missing = collect_handoff(
            repo_root, entry=entry, relative_worktree=relative_worktree,
            handoff_path=handoff_path, into=into,
            allow_missing_handoff=allow_missing_handoff, max_bytes=max_bytes,
            resolved_entry_id=resolved_entry_id, collected_to=collected_to,
            read_handoff=read_handoff, write_collected=write_collected,
        )
        if resolved_entry_id is not None:
            note = _reason_note(
                "collect-worktree", reason,
                flag="--allow-missing-handoff" if missing else "",
            )
            reason_recorded = bool(note)
            _mark(
                repo_root, resolved_entry_id, "collected", now=now,
                note=note, collected_to=collected_to,
            )
    if resolved_entry_id is not None and not reason_recorded:
        _note(
            repo_root, resolved_entry_id, now=now,
            note=_reason_note("collect-worktree", reason),
        )
    return finish_collect(
        repo_root, relative_worktree=relative_worktree,
        resolved_entry_id=resolved_entry_id, collected_to=collected_to,
        reason=reason, now=now, runner=runner, release=release,
        release_fn=release_fn,
    )
