"""閾値判定（Issue #488「提案挙動」4.）。

判定は2本で、どちらかが立てば「異常」とする。

* ``BASELINE_EXCEEDED`` — 派生 Issue/PR が基線 :data:`~defect_metrics.model.BASELINE_DERIVED_PER_PR`
  （0.68・Issue #488「現状と根拠」の実測）を**超えた**場合。
* ``TRAILING_REGRESSION`` — 直近4週（レポート窓の直前に接続する28日）の派生 Issue/PR に対し、
  レポート窓の値が **50% 以上悪化**（``current >= trailing * 1.5``）した場合。

**異常でなければ何も報告しない**（Issue #488）。``alerts`` が空のとき呼び出し側は
アラート文言を一切出力しない。レポート JSON 自体は毎回 publish するが、これは
「異常の報告」ではなく計測結果の保存であり、報告経路（#461）へ流すのは
``anomaly: true`` のときだけである。

2本で比較の精度が違う。意図的な使い分けである。

* 基線比較は**表示精度（小数2桁）どうし**で行う。基線定数 0.68 は実測 15/22 = 0.6818… を
  2桁で記録した値であり、厳密値で比べると基線の窓自身が「基線超過」になってしまう
  （:attr:`~defect_metrics.metrics.WindowMetrics.derived_per_pr_rounded` の docstring 参照）。
* 直近4週比較は**有理数の厳密値**で行う。両辺とも同じ計測から出た比であり丸め記録では
  ないうえ、float だと ``0.2 * 1.5 == 0.30000000000000004`` の表現誤差で「ちょうど1.5倍」が
  裏返るため（:attr:`~defect_metrics.metrics.WindowMetrics.derived_per_pr_exact`）。

比較不能な条件（分母0・直近4週のデータが無い）は「異常なし」に倒さず ``skipped``
として明示する——観測できていないことを「正常」と読ませないため（PR4）。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .metrics import WindowMetrics
from .model import BASELINE_DERIVED_PER_PR, RATIO_DIGITS, REGRESSION_FACTOR

#: 有理数での厳密比較に使う 1.5（float の 1.5 は 2 進で厳密なので変換は無損失だが、
#: 定数の意味を1箇所に閉じるため文字列経由で作る）。
_REGRESSION_FRACTION = Fraction(str(REGRESSION_FACTOR))

BASELINE_EXCEEDED = "BASELINE_EXCEEDED"
TRAILING_REGRESSION = "TRAILING_REGRESSION"

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
            "anomaly": self.anomaly,
            "alerts": [a.as_dict() for a in self.alerts],
            "skipped": [s.as_dict() for s in self.skipped],
        }

    def render_alert_lines(self) -> list[str]:
        """異常時にだけ人間向けの行を返す（異常でなければ空リスト）。"""
        return [f"{a.code}: {a.detail}" for a in self.alerts]


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
