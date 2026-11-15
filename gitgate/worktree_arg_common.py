"""Shared flag parsing and scalar validation for worktree commands."""

from __future__ import annotations
from typing import Sequence
from issue_start.worktree_ledger import ENTRY_ID_RE
from .worktree_models import WorktreeError

_MAX_REASON_LEN = 1000

def _reject_control_chars(value: str, what: str) -> None:
    if "\n" in value or "\r" in value or "\0" in value:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", f"{what} contains control characters")


def _validate_entry_id(value: str) -> str:
    if not isinstance(value, str) or not ENTRY_ID_RE.fullmatch(value):
        raise WorktreeError("WORKTREE_ENTRY_ID_INVALID", repr(value))
    return value


def _validate_reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorktreeError("WORKTREE_REASON_EMPTY")
    _reject_control_chars(value, "reason")
    if len(value) > _MAX_REASON_LEN:
        raise WorktreeError("WORKTREE_REASON_TOO_LONG", str(len(value)))
    return value


def _parse_flags(
    args: Sequence[str],
    *,
    value_flags: set,
    bool_flags: set,
    allow_positional: bool,
) -> tuple:
    """固定 schema の flag parse。未知/重複 flag・値欠落は拒否する（副作用なし）。"""
    positional: str | None = None
    index = 0
    if allow_positional and args and not args[0].startswith("-"):
        positional = args[0]
        index = 1
    values: dict[str, str] = {}
    flags: set = set()
    while index < len(args):
        token = args[index]
        if token in bool_flags:
            if token in flags:
                raise WorktreeError("WORKTREE_ARGUMENT_INVALID", f"duplicate {token}")
            flags.add(token)
            index += 1
            continue
        if token in value_flags:
            if token in values or index + 1 >= len(args):
                raise WorktreeError("WORKTREE_ARGUMENT_INVALID", token)
            values[token] = args[index + 1]
            index += 2
            continue
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", token)
    return positional, values, flags
