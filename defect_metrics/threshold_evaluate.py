"""Evaluate reporting-window metrics against fixed thresholds."""

from __future__ import annotations
from fractions import Fraction
from .metrics import WindowMetrics
from .model import BASELINE_DERIVED_PER_PR, RATIO_DIGITS, REGRESSION_FACTOR
from .threshold_types import Alert, Evaluation, Skip, BASELINE_EXCEEDED, TRAILING_REGRESSION, SKIP_NO_DENOMINATOR, SKIP_NO_TRAILING_DATA

_REGRESSION_FRACTION = Fraction(str(REGRESSION_FACTOR))


def _fmt(value: float | Fraction | None) -> str:
    return "n/a" if value is None else f"{round(float(value), RATIO_DIGITS)}"


def evaluate(current: WindowMetrics, trailing: WindowMetrics | None) -> Evaluation:
    """レポート窓 ``current`` を基線と直近4週 ``trailing`` に照らして判定する。"""
    alerts: list[Alert] = []
    skipped: list[Skip] = []

    current_rate = current.derived_per_pr_rounded
    if current_rate is None:
        skipped.append(
            Skip(
                SKIP_NO_DENOMINATOR,
                "レポート窓に merge された PR が 0 件のため派生 Issue/PR を算出できない"
                "（異常なしとは判定していない）。",
            )
        )
        return Evaluation(alerts=(), skipped=tuple(skipped))

    if current_rate > BASELINE_DERIVED_PER_PR:
        alerts.append(
            Alert(
                BASELINE_EXCEEDED,
                f"派生 Issue/PR = {_fmt(current_rate)} が基線 {BASELINE_DERIVED_PER_PR} を超過"
                f"（派生 {current.derived_issues} 件 / merged PR {current.merged_prs} 件）。",
            )
        )

    current_exact = current.derived_per_pr_exact
    trailing_rate = trailing.derived_per_pr_exact if trailing is not None else None
    if trailing_rate is None or current_exact is None:
        skipped.append(
            Skip(
                SKIP_NO_TRAILING_DATA,
                "直近4週の窓に merge された PR が 0 件（またはデータ未取得）のため"
                "「直近4週平均から 50% 以上悪化」を判定できない（異常なしとは判定していない）。",
            )
        )
    elif trailing_rate == 0:
        # 直近4週が 0 のとき current * 1.5 の比較は常に成立してしまうため、
        # 「0 から増えたか」だけを見る（0 → 0 を悪化と呼ばない）。
        if current_exact > 0:
            alerts.append(
                Alert(
                    TRAILING_REGRESSION,
                    f"直近4週の派生 Issue/PR が 0 だったのに対しレポート窓は {_fmt(current_exact)}"
                    "（0 からの増加は 50% 以上の悪化として扱う）。",
                )
            )
    elif current_exact >= trailing_rate * _REGRESSION_FRACTION:
        alerts.append(
            Alert(
                TRAILING_REGRESSION,
                f"派生 Issue/PR = {_fmt(current_exact)} が直近4週 {_fmt(trailing_rate)} の"
                f"{REGRESSION_FACTOR} 倍以上（50% 以上悪化）。",
            )
        )

    return Evaluation(alerts=tuple(alerts), skipped=tuple(skipped))
