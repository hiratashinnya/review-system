"""Worktree errors and immutable request/outcome data shared by all worktree verbs."""

from __future__ import annotations

from dataclasses import dataclass

class WorktreeError(Exception):
    """worktree を一意に特定できない/解放してよいと言えない場合の fail-close error。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


# --- 引数スキーマ --------------------------------------------------------------


@dataclass(frozen=True)
class ReleaseRequest:
    worktree_path: str
    entry_id: str | None = None
    force_uncollected: bool = False
    reason: str = ""


@dataclass(frozen=True)
class CollectRequest:
    entry_id: str | None = None
    worktree_path: str | None = None
    handoff_path: str | None = None
    into: str | None = None
    allow_missing_handoff: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ForgetRequest:
    entry_id: str
    reason: str


@dataclass(frozen=True)
class SweepRequest:
    """``worktree-sweep-abandoned`` の引数（Issue #502）。

    ``no_live_dispatch`` は「live な dispatch が1つも無いことを呼び出し元が観測した」という
    **申告**であり、これが無ければ掃引は何もしない（#423 の入れ子委譲中 ``running`` を
    誤って解放しないための構造的な条件）。
    """

    reason: str
    no_live_dispatch: bool = False


@dataclass(frozen=True)
class SweepEntryOutcome:
    entry_id: str
    worktree_path: str
    action: str
    detail: str = ""


@dataclass(frozen=True)
class ReleaseOutcome:
    worktree_path: str
    entry_id: str | None
    removed: bool
    status: str


@dataclass(frozen=True)
class CollectOutcome:
    worktree_path: str
    entry_id: str | None
    collected_to: str | None
    released: bool
