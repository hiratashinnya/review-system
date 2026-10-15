"""Immutable records and report windows."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from .timestamps import format_timestamp


@dataclass(frozen=True)
class Window:
    """UTC の半開区間 ``[start, end)``。"""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Window の境界は tz-aware でなければならない")
        if self.end <= self.start:
            raise ValueError(f"window end({self.end}) は start({self.start}) より後でなければならない")

    def contains(self, moment: datetime | None) -> bool:
        """``start <= moment < end`` か。``None``（未 close 等）は常に False。"""
        if moment is None:
            return False
        return self.start <= moment < self.end

    @property
    def days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400.0

    def shifted_back(self, span: timedelta) -> "Window":
        """この窓の直前に接続する幅 ``span`` の窓（``[start - span, start)``）を返す。"""
        return Window(start=self.start - span, end=self.start)

    def as_dict(self) -> dict[str, object]:
        return {
            "start": format_timestamp(self.start),
            "end": format_timestamp(self.end),
            "days": self.days,
            "boundary": "start <= t < end (UTC)",
        }


@dataclass(frozen=True)
class IssueRecord:
    """計測に必要な Issue の最小情報（``gh issue list --json`` 由来）。"""

    number: int
    created_at: datetime
    closed_at: datetime | None
    body: str


@dataclass(frozen=True)
class PullRequestRecord:
    """計測に必要な merged PR の最小情報（``gh pr list --json`` 由来）。"""

    number: int
    merged_at: datetime
