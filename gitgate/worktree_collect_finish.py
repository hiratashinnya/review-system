"""Finish collection; only an already safe handoff permits deferred release."""

from issue_start.worktree_ledger import DEFERRED_RELEASE_STATUS
from .worktree_models import CollectOutcome, WorktreeError
from .worktree_ledger_access import _mark
from .worktree_release_safety import _is_worktree_lock_failure

def finish_collect(repo_root, *, relative_worktree, resolved_entry_id, collected_to,
                   reason, now, runner, release, release_fn):
    if not release:
        return CollectOutcome(
            relative_worktree, resolved_entry_id, collected_to, released=False
        )
    try:
        outcome = release_fn(
            repo_root,
            relative_worktree,
            entry_id=resolved_entry_id,
            force_uncollected=resolved_entry_id is None,
            reason=(
                (reason or "collect-worktree: 台帳エントリの無い worktree を回収後に解放")
                if resolved_entry_id is None
                else ""
            ),
            now=now,
            runner=runner,
        )
    except WorktreeError as exc:
        if (
            resolved_entry_id is not None
            and collected_to is not None
            and exc.reason == "WORKTREE_REMOVE_FAILED"
            and _is_worktree_lock_failure(exc.detail)
        ):
            _mark(
                repo_root,
                resolved_entry_id,
                DEFERRED_RELEASE_STATUS,
                now=now,
                note=(
                    "collect-worktree: handoff は回収済み（collected_to）だが git の "
                    "worktree ロックで削除できなかった。削除を issue-start-gate へ遅延する"
                    f"（Issue #464 / {(exc.detail or '')[:160]}）"
                ),
            )
            return CollectOutcome(
                relative_worktree, resolved_entry_id, collected_to, released=False
            )
        raise
    return CollectOutcome(
        relative_worktree, resolved_entry_id, collected_to, released=outcome.status == "released"
    )
