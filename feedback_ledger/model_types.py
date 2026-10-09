"""Finding record used by feedback ledger validators."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """1件の検査結果。``level`` が ``ERROR`` のとき CLI は終了コード 4 で落とす。"""

    rule: str
    level: str
    locus: str
    message: str

    def render(self) -> str:
        return f"{self.level}: [{self.rule}] {self.locus}: {self.message}"
