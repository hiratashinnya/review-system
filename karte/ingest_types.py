"""``ingest-review`` の各段が受け渡す結果の型（データのみ。ロジックは持たない）。"""

from pathlib import Path
from typing import Any, NamedTuple

from .model import Karte


class AcceptedFinding(NamedTuple):
    """取り込める指摘 1 件。``item`` は :class:`karte.model.ReviewFinding`。"""

    finding_id: str
    item: Any
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
    accepted: list
    errors: list


class IngestOutcome(NamedTuple):
    """反映結果。``excluded`` は ``distinct_from`` の除外ペア（監査用）。"""

    created: list
    resolved: list
    excluded: list


class IngestResult(NamedTuple):
    """取り込み 1 回分の結果。出力整形（:mod:`karte.ingest_report`）が読む。"""

    karte: Karte
    path: Path
    issue: int
    round_no: int
    accepted: list
    outcome: IngestOutcome
