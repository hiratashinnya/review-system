"""試行と結果の記録。移設した設計理由は .ai/rationale/karte-module-split.md を参照。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Attempt:
    """1 回の是正試行の宣言（機械比較可能ヘッダ）。"""

    number: int
    round: int
    finding_ids: list
    root_cause: str
    change_kind: str
    targets: list
    diagnosis: str = ""


@dataclass
class Result:
    """Attempt の処置結果（実測 touched-set の記録先・追記のみ）。"""

    attempt: int
    finding_ids: list
    touched: list
    outcome: str
    note: str = ""
