"""Parse forget and sweep arguments without performing I/O."""

from __future__ import annotations
from typing import Sequence
from .worktree_models import ForgetRequest, SweepRequest, WorktreeError
from .worktree_arg_common import _parse_flags, _validate_entry_id, _validate_reason

def parse_worktree_forget_args(args: Sequence[str]) -> ForgetRequest:
    _positional, values, _flags = _parse_flags(
        args,
        value_flags={"--entry", "--reason"},
        bool_flags=set(),
        allow_positional=False,
    )
    if "--entry" not in values:
        raise WorktreeError("WORKTREE_ARGUMENT_INVALID", "missing --entry")
    if "--reason" not in values:
        # 理由なしの ``abandoned`` は「なぜ諦めたか」を失う＝後から再構成できない一次情報の
        # 取りこぼしになる（PR8 区分1）。必須にして構造的に防ぐ。
        raise WorktreeError("WORKTREE_FORGET_REASON_REQUIRED")
    return ForgetRequest(
        entry_id=_validate_entry_id(values["--entry"]),
        reason=_validate_reason(values["--reason"]),
    )


def parse_worktree_sweep_args(args: Sequence[str]) -> SweepRequest:
    """``worktree-sweep-abandoned --no-live-dispatch --reason <text>`` を parse する。

    どちらのフラグも**必須**にする。``--reason`` は台帳へ残す一次情報（なぜ掃引したか）で、
    ``--no-live-dispatch`` は「live な dispatch が1つも無いことを観測した」という申告
    （Issue #423 の保留 ``running`` を誤解放しないための前提）。欠けたら git も台帳も一切
    触らずに fail-close する。
    """
    _positional, values, flags = _parse_flags(
        args,
        value_flags={"--reason"},
        bool_flags={"--no-live-dispatch"},
        allow_positional=False,
    )
    if "--reason" not in values:
        raise WorktreeError("WORKTREE_SWEEP_REASON_REQUIRED")
    if "--no-live-dispatch" not in flags:
        raise WorktreeError(
            "WORKTREE_SWEEP_PRECONDITION_MISSING",
            "--no-live-dispatch が要る（live な dispatch が1つも無いことを観測した地点"
            "＝レートリミット復帰イベントからのみ呼ぶ）",
        )
    return SweepRequest(
        reason=_validate_reason(values["--reason"]), no_live_dispatch=True
    )


# --- パス検証 ------------------------------------------------------------------
