"""``--round`` の補完結果の型（データのみ。補完の実装は :mod:`karte.pointer_completion`）。"""

from dataclasses import dataclass
from enum import Enum


class MissingRoundHint(Enum):
    """進行ポインタが ``round`` を欠くとき、呼び出し元の verb に応じて添える案内。"""

    FIRST_INGEST = "（初回の取り込みは `--round 1` を明示する）"
    RUN_INGEST_FIRST = "（`--round` を明示するか、先に `ingest-review` を実行する）"


@dataclass(frozen=True)
class ResolvedRound:
    """検証済みの ``round`` と、その出所（``--round`` の明示か、進行ポインタからの補完か）。"""

    number: int
    explicit: bool
