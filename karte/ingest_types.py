"""``ingest-review`` の各段が受け渡す結果の型（データのみ。ロジックは持たない）。"""

from pathlib import Path
from typing import NamedTuple

from .model import Karte, ReviewFinding


class AcceptedFinding(NamedTuple):
    """取り込める指摘 1 件。"""

    finding_id: str
    item: ReviewFinding
    is_new: bool


class Assigned(NamedTuple):
    """ブロックに finding ID を割り当てられた。"""

    finding_id: str
    is_new: bool
    next_seq: int


class Rejected(NamedTuple):
    """finding ID を割り当てられなかった（``message`` が拒否理由）。"""

    message: str
    next_seq: int


class CollectResult(NamedTuple):
    accepted: list[AcceptedFinding]
    errors: list[str]


class IngestOutcome(NamedTuple):
    """反映結果。``excluded`` は ``distinct_from`` の除外ペア（監査用）。"""

    created: list[str]
    resolved: list[str]
    excluded: list[str]


class IngestResult(NamedTuple):
    """取り込み 1 回分の結果。出力整形（:mod:`karte.ingest_report`）が読む。"""

    karte: Karte
    path: Path
    issue: int
    round_no: int
    accepted: list[AcceptedFinding]
    outcome: IngestOutcome
