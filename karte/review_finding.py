"""レビューレポート 1 件分の型（台帳へ取り込む前の素・データのみ）。"""

from dataclasses import dataclass


@dataclass
class ReviewFinding:
    """レビューレポート 1 件分（台帳へ取り込む前の素）。"""

    title: str
    finding_id: str | None  # None＝``### new``＝採番を CLI に委ねる
    harm: str
    harm_detail: str
    severity: str
    locus: list
    summary: str
    evidence: str
    expected: str
    recheck: str
    scope: str                    # ``in``/``out``（必須・Issue #495。免除力は持たない）
    lineno: int
    status: str = "open"          # ``resolved`` と**明示**したときだけ解消（K-06）
    distinct_from: tuple = ()     # 再発番判定を無効化する相手 ID（K-05・ペア限定）
    disposition: str = ""         # 以下4欄はオーナー判断の記録（任意・未決定なら空）
    deferred_to: str = ""
    waived_by: str = ""
    waived_reason: str = ""
