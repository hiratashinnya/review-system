"""Public worktree lifecycle facade; safety rationale lives in .ai/rationale."""

from __future__ import annotations
import hashlib
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence
from issue_start.worktree_ledger import (
    DEFERRED_RELEASE_STATUS, ENTRY_ID_RE, WORKTREE_PATH_RE, LedgerError,
    add_note, main_worktree_root, mark, read_ledger,
)
from .worktree_models import (
    WorktreeError, ReleaseRequest, CollectRequest, ForgetRequest, SweepRequest,
    SweepEntryOutcome, ReleaseOutcome, CollectOutcome,
)
from .worktree_arg_common import _reject_control_chars, _validate_entry_id, _validate_reason, _parse_flags, _MAX_REASON_LEN
from .worktree_arg_release import parse_worktree_release_args, parse_collect_worktree_args
from .worktree_arg_lifecycle import parse_worktree_forget_args, parse_worktree_sweep_args
from .worktree_path_validation import validate_worktree_path, resolve_within
from .worktree_handoff_paths import HANDOFF_DIR_PARTS, HANDOFF_FILENAME_RE, _SAFE_PATH_PART_RE, validate_handoff_relpath, validate_collect_dest
from .worktree_git_runtime import _run_git, _fetch_env
from .worktree_git_records import worktree_records, linked_worktree_paths, _is_git_managed
from .worktree_config import FETCH_TIMEOUT_SECONDS, DEFAULT_MAX_HANDOFF_BYTES, COLLECTED_DIRNAME
from .worktree_ledger_access import _entries, find_entry, _mark, _note
from .worktree_release_safety import _reason_note, _is_worktree_lock_failure, _remove_worktree_dir
from .worktree_branch_cleanup import _cleanup_branch_ref
from .worktree_release_flow import worktree_release
from .worktree_handoff_io import _read_handoff, _write_collected, _ensure_collected_dir
from .worktree_collect_flow import collect_worktree_flow as _collect_worktree_flow
from .worktree_forget import worktree_forget
from .worktree_sweep_handoff import _own_handoff
from .worktree_sweep_clean import _is_worktree_clean, _locked_worktree_paths
from .worktree_sweep_discard import _is_discardable
from .worktree_sweep_state import SWEEP_MARKER, _sweep_stale, sweep_preflight
from .worktree_sweep_recovery import sweep_recover
from .worktree_sweep import run_sweep as _run_sweep

def collect_worktree(
    repo_root,
    *,
    entry_id: str | None = None,
    worktree_path: str | None = None,
    handoff_path: str | None = None,
    into: str | None = None,
    allow_missing_handoff: bool = False,
    reason: str = "",
    now,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    max_bytes: int = DEFAULT_MAX_HANDOFF_BYTES,
    release: bool = True,
) -> CollectOutcome:
    """Collect a handoff and release its worktree; retain facade injection seams."""
    return _collect_worktree_flow(
        repo_root, entry_id=entry_id, worktree_path=worktree_path,
        handoff_path=handoff_path, into=into,
        allow_missing_handoff=allow_missing_handoff, reason=reason,
        now=now, runner=runner, max_bytes=max_bytes, release=release,
        read_handoff=_read_handoff, write_collected=_write_collected,
        release_fn=worktree_release,
    )


def _sweep_one(repo_root, entry, *, now, reason, locked, runner) -> SweepEntryOutcome:
    """Preserve the original per-entry entrypoint and collect patch seam."""
    handoff, how, outcome = sweep_preflight(
        repo_root, entry, now=now, reason=reason, locked=locked, runner=runner,
    )
    if outcome is not None:
        return outcome
    return sweep_recover(
        repo_root, entry, handoff=handoff, how=how, now=now, reason=reason,
        runner=runner, collect_fn=collect_worktree,
    )


def sweep_abandoned_running(
    repo_root,
    *,
    now,
    reason: str,
    no_live_dispatch: bool = False,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list:
    """Safely sweep only when the caller has observed no live dispatch."""
    return _run_sweep(
        repo_root, now=now, reason=reason,
        no_live_dispatch=no_live_dispatch, runner=runner, sweep_one=_sweep_one,
    )

def default_repo_root(candidate=None) -> Path:
    """CLI 既定の repo-root（linked worktree から起動されても main worktree へ収束させる）。"""
    try:
        return main_worktree_root(Path.cwd() if candidate is None else candidate)
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc
