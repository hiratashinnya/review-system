"""Parse release and collect arguments without performing I/O."""

from __future__ import annotations
from typing import Sequence
from .worktree_models import CollectRequest, ReleaseRequest, WorktreeError
from .worktree_arg_common import _parse_flags, _validate_entry_id, _validate_reason
from .worktree_path_validation import validate_worktree_path

def parse_worktree_release_args(args: Sequence[str]) -> ReleaseRequest:
    positional, values, flags = _parse_flags(
        args,
        value_flags={"--entry", "--reason"},
        bool_flags={"--force-uncollected"},
        allow_positional=True,
    )
    if positional is None:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", "missing <worktree-path>")
    force = "--force-uncollected" in flags
    reason = values.get("--reason", "")
    # `--force-uncollected` があれば必須、単独で渡されたときも検証する（受理した理由は
    # 必ず台帳へ載るので、制御文字・過長のものをここで落とす＝F-354-04）。
    if force or reason:
        _validate_reason(reason)
    return ReleaseRequest(
        worktree_path=validate_worktree_path(positional),
        entry_id=_validate_entry_id(values["--entry"]) if "--entry" in values else None,
        force_uncollected=force,
        reason=reason,
    )


def parse_collect_worktree_args(args: Sequence[str]) -> CollectRequest:
    positional, values, flags = _parse_flags(
        args,
        value_flags={"--entry", "--handoff", "--into", "--reason"},
        bool_flags={"--allow-missing-handoff"},
        allow_positional=True,
    )
    entry_id = _validate_entry_id(values["--entry"]) if "--entry" in values else None
    if positional is None and entry_id is None:
        raise WorktreeError(
            "WORKTREE_ARGUMENT_INVALID", "either <worktree-path> or --entry is required"
        )
    allow_missing = "--allow-missing-handoff" in flags
    reason = values.get("--reason", "")
    if allow_missing or reason:
        _validate_reason(reason)
    if positional is not None and entry_id is None and "--handoff" not in values:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", "missing --handoff")
    return CollectRequest(
        entry_id=entry_id,
        worktree_path=validate_worktree_path(positional) if positional is not None else None,
        handoff_path=values.get("--handoff"),
        into=values.get("--into"),
        allow_missing_handoff=allow_missing,
        reason=reason,
    )
