"""Immutable threshold evaluation results."""

from __future__ import annotations
from dataclasses import dataclass
from .model import BASELINE_DERIVED_PER_PR, REGRESSION_FACTOR

BASELINE_EXCEEDED = "BASELINE_EXCEEDED"
TRAILING_REGRESSION = "TRAILING_REGRESSION"
TRAILING_AGGREGATION = "pooled"
TRAILING_AGGREGATION_DETAIL = ("直近28日をひとまとめの窓として derived_issues / merged_prs を取るプールド比。週次比4本の平均ではない（Issue #488 本文の「直近4週平均」という文言との差異）。少 PR 週の比が平均を支配することと、分母0の週の扱いが定義できないことを避けるための選択（根拠＝defect_metrics/threshold.py の docstring・defect_metrics/README.md §3）。")
SKIP_NO_DENOMINATOR = "NO_DENOMINATOR"
SKIP_NO_TRAILING_DATA = "NO_TRAILING_DATA"


@dataclass(frozen=True)
class Alert:
    code: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class Skip:
    code: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class Evaluation:
    alerts: tuple[Alert, ...]
    skipped: tuple[Skip, ...]

    @property
    def anomaly(self) -> bool:
        return bool(self.alerts)

    def as_dict(self) -> dict[str, object]:
        return {
            "baseline_derived_per_pr": BASELINE_DERIVED_PER_PR,
            "regression_factor": REGRESSION_FACTOR,
            "trailing_aggregation": {
                "method": TRAILING_AGGREGATION,
                "detail": TRAILING_AGGREGATION_DETAIL,
            },
            "anomaly": self.anomaly,
            "alerts": [a.as_dict() for a in self.alerts],
            "skipped": [s.as_dict() for s in self.skipped],
        }

    def render_alert_lines(self) -> list[str]:
        """異常時にだけ人間向けの行を返す（異常でなければ空リスト）。"""
        return [f"{a.code}: {a.detail}" for a in self.alerts]
