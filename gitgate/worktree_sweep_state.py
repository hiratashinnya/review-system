"""Per-entry lock, owner, and discardability gates before marking stopped."""

from pathlib import Path
from .worktree_models import WorktreeError, SweepEntryOutcome
from .worktree_ledger_access import _mark
from .worktree_sweep_handoff import _own_handoff
from .worktree_sweep_discard import _is_discardable

SWEEP_MARKER = "worktree-sweep-abandoned"

def _sweep_stale(repo_root, entry_id, *, now, note) -> None:
    try:
        _mark(repo_root, entry_id, "stale", now=now, note=note)
    except WorktreeError:
        # 記録できなくても掃引は続ける（残留は gate の deny が別途拾う）。
        pass

def sweep_preflight(repo_root, entry, *, now, reason, locked, runner):
    entry_id = entry["entry_id"]
    relative = entry["worktree_path"]
    try:
        resolved = str((Path(repo_root).resolve() / relative).resolve())
    except OSError:
        resolved = ""
    if resolved and resolved in locked:
        # ハーネスがロックしている＝live な dispatch が掴んでいる。触らない（#423 の保護）。
        return None, None, SweepEntryOutcome(
            entry_id, relative, "kept-locked", "git が locked と報告した worktree"
        )

    handoff, how = _own_handoff(repo_root, entry)
    if how in ("ambiguous", "unreadable", "unidentifiable"):
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 自分の handoff を一意に決められない（{how}）ため解放しない。"
                f"主文脈が collect-worktree / worktree-forget で処置する（Issue #502）: {reason}"
            ),
        )
        return None, None, SweepEntryOutcome(entry_id, relative, "kept-unresolved", how)

    if how == "empty":
        discardable, why = _is_discardable(repo_root, entry, runner=runner)
        if not discardable:
            _sweep_stale(
                repo_root,
                entry_id,
                now=now,
                note=(
                    f"{SWEEP_MARKER}: handoff が無く、捨ててよいと確認できなかったため解放しない"
                    f"（{why}）。主文脈が内容を確認して処置する（Issue #502）: {reason}"
                ),
            )
            return None, None, SweepEntryOutcome(entry_id, relative, "kept-unsafe", why)

    _mark(
        repo_root,
        entry_id,
        "stopped",
        now=now,
        note=(
            f"{SWEEP_MARKER}: live な dispatch が1つも無い地点（レートリミット復帰）で "
            f"running が残っていたため、異常終了として停止を確定した（Issue #502・handoff={how}）"
            f": {reason}"
        ),
    )
    return handoff, how, None
