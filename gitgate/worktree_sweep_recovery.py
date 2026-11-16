"""Collect first, check clean, then retry the release stage."""

from .worktree_models import WorktreeError, SweepEntryOutcome
from .worktree_sweep_clean import _is_worktree_clean
from .worktree_sweep_state import SWEEP_MARKER, _sweep_stale

def sweep_recover(repo_root, entry, *, handoff, how, now, reason, runner, collect_fn):
    entry_id = entry["entry_id"]
    relative = entry["worktree_path"]
    # A later clean-check failure must not discard an already collected handoff.
    try:
        collected = collect_fn(
            repo_root,
            entry_id=entry_id,
            handoff_path=handoff,
            allow_missing_handoff=handoff is None,
            reason=f"{SWEEP_MARKER}: {reason}",
            now=now,
            runner=runner,
            release=False,
        )
    except WorktreeError as exc:
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 回収に失敗した（{exc.reason}）。"
                f"主文脈が処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-error", exc.reason)

    if how == "unique":
        # handoff があっても削除前には clean を確認する（F-502-01）。
        # handoff 不在は _is_discardable で clean と origin 包含を確認済み。
        clean, why = _is_worktree_clean(repo_root, entry, runner=runner)
        if not clean:
            _sweep_stale(
                repo_root,
                entry_id,
                now=now,
                note=(
                    f"{SWEEP_MARKER}: handoff は回収した"
                    f"（collected_to={collected.collected_to or '-'}）が、作業ツリーが clean と"
                    f"確認できなかったため解放しない（{why}）。主文脈が内容を確認して処置する"
                    f"（Issue #502）: {reason}"
                ),
            )
            return SweepEntryOutcome(entry_id, relative, "kept-unsafe", why)

    # 段6 だけをやり直す（エントリは `collected`）。`release_pending` への遅延（Issue #464）を
    # 含む解放段の契約をそのまま再利用するため、`worktree_release` を直接呼ばない。
    # `reason` は回収段で既に台帳へ書いているので渡さない（同じ理由を2回 notes に載せない）。
    try:
        outcome = collect_fn(
            repo_root,
            entry_id=entry_id,
            now=now,
            runner=runner,
        )
    except WorktreeError as exc:
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 解放に失敗した（{exc.reason}）。"
                f"主文脈が処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-error", exc.reason)
    return SweepEntryOutcome(
        entry_id,
        relative,
        "released" if outcome.released else "release-pending",
        outcome.collected_to or "",
    )
