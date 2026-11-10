"""指摘の記録。移設した設計理由は .ai/rationale/karte-module-split.md を参照。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .finding_id import parse_finding_id
from .finding_handoff_record import HandoffRecord
from .vocabulary import CLEARING_DISPOSITIONS, CLEARING_HARM, DEFAULT_SCOPE


@dataclass
class Finding:
    """ID 付き指摘（台帳の 1 行）。"""

    id: str
    status: str = "open"
    harm: str = "real"
    harm_detail: str = ""
    severity: str = "major"
    # ``locus`` はリスト（ミラー複数ファイルの同一欠陥を 1 指摘で指す・Issue #341）。
    locus: list = field(default_factory=list)
    summary: str = ""
    # ``evidence``＝そう言える根拠（読んだファイル/行・実行したコマンドと結果）。
    evidence: str = ""
    # ``expected``＝解消の条件、``recheck``＝次ラウンドの判定手順（ラウンドをまたぐため台帳に持つ）。
    expected: str = ""
    recheck: str = ""
    # ``scope``＝レビューアの申告（免除力なし）。既定は ``scope`` 無しの既存カルテの移行措置。
    scope: str = DEFAULT_SCOPE
    # ``disposition``＝オーナー判断の記録。空文字＝未決定。
    disposition: str = ""
    deferred_to: str = ""
    waived_by: str = ""
    waived_reason: str = ""
    rounds: list = field(default_factory=list)
    resolved_round: int | None = None
    handoff: HandoffRecord | None = None

    @property
    def seq(self) -> int:
        return parse_finding_id(self.id)[1]

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def cleared_by_disposition(self) -> bool:
        """設計理由は .ai/rationale/karte-module-split.md を参照。"""
        return self.harm == CLEARING_HARM and self.disposition in CLEARING_DISPOSITIONS

    @property
    def needs_remediation(self) -> bool:
        """設計理由は .ai/rationale/karte-module-split.md を参照。"""
        return self.is_open and not self.cleared_by_disposition

    @property
    def needs_disposition(self) -> bool:
        """設計理由は .ai/rationale/karte-module-split.md を参照。"""
        return self.is_open and self.harm == "real" and not self.disposition

    def max_consecutive_rounds(self) -> int:
        """未解消のまま連続して挙げられたラウンド数の最大値（無進捗判定に使う）。"""
        best = 0
        run = 0
        previous = None
        for value in sorted(set(self.rounds)):
            run = run + 1 if previous is not None and value == previous + 1 else 1
            previous = value
            best = max(best, run)
        return best
