"""Dispatch abandoned-running sweeps; isolate failures per ledger entry."""

from .worktree_models import SweepEntryOutcome
from .worktree_arg_common import _validate_reason
from .worktree_ledger_access import _entries
from .worktree_sweep_clean import _locked_worktree_paths

def run_sweep(repo_root, *, now, reason, no_live_dispatch, runner, sweep_one):
    """Without an explicit idle observation, touch neither Git nor the ledger."""
    if not no_live_dispatch:
        return []
    _validate_reason(reason)
    candidates = [
        entry
        for entry in _entries(repo_root)
        if entry.get("status") == "running"
        and isinstance(entry.get("entry_id"), str)
        and isinstance(entry.get("worktree_path"), str)
        and entry.get("worktree_path")
    ]
    if not candidates:
        return []
    try:
        locked = _locked_worktree_paths(repo_root, runner=runner)
    except Exception:  # noqa: BLE001 - 判定材料が読めないなら何もしない（fail-safe）
        return []

    outcomes: list = []
    for entry in candidates:
        entry_id = entry["entry_id"]
        relative = entry["worktree_path"]
        try:
            outcomes.append(
                sweep_one(
                    repo_root,
                    entry,
                    now=now,
                    reason=reason,
                    locked=locked,
                    runner=runner,
                )
            )
        except Exception as exc:  # noqa: BLE001 - 1件の事故で掃引全体を止めない
            outcomes.append(
                SweepEntryOutcome(
                    entry_id, relative, "kept-error", type(exc).__name__
                )
            )
    return outcomes
