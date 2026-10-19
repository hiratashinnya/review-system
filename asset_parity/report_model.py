"""Presence matrix values and aggregate counts."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from . import staleness as staleness_mod
from .inventory import Asset

STATUS_PRESENT = "present"
STATUS_MISSING = "missing"
STATUS_EXEMPT = "exempt"
STATUS_NA = "na"


@dataclasses.dataclass(frozen=True)
class Cell:
    status: str
    path: Path | None = None
    reason: str | None = None
    stale: "staleness_mod.StaleSignal | None" = None


@dataclasses.dataclass(frozen=True)
class AssetRow:
    asset: Asset
    cells: dict[str, Cell]


@dataclasses.dataclass(frozen=True)
class Report:
    rows: list[AssetRow]
    orphans: dict[str, list[str]]  # tree -> sorted asset names present only in the mirror

    @property
    def missing_count(self) -> int:
        return sum(1 for row in self.rows for cell in row.cells.values()
                   if cell.status == STATUS_MISSING)

    @property
    def stale_flag_count(self) -> int:
        return sum(1 for row in self.rows for cell in row.cells.values()
                   if cell.stale is not None and cell.stale.flagged)


