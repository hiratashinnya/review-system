"""Window metric values and derived ratios."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .model import RATIO_DIGITS, Window


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _rounded(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, RATIO_DIGITS)


@dataclass(frozen=True)
class WindowMetrics:
    """1つの窓に対する指標一式。比率は丸め前の厳密値で保持する。"""

    window: Window
    merged_prs: int
    created_issues: int
    derived_issues: int
    closed_issues: int
    derived_issue_numbers: tuple[int, ...] = ()

    @property
    def issues_per_pr(self) -> float | None:
        """副指標＝窓内作成の全 Issue / 窓内 merged PR。"""
        return _ratio(self.created_issues, self.merged_prs)

    @property
    def derived_per_pr(self) -> float | None:
        """主指標＝窓内作成の派生 Issue / 窓内 merged PR。"""
        return _ratio(self.derived_issues, self.merged_prs)

    @property
    def derived_per_pr_exact(self) -> Fraction | None:
        """有理数の主指標比率（閾値境界での丸め誤差を防ぐ）。"""
        if self.merged_prs == 0:
            return None
        return Fraction(self.derived_issues, self.merged_prs)

    @property
    def derived_per_pr_rounded(self) -> float | None:
        """基線比較用に表示精度へ丸めた主指標比率。"""
        return _rounded(self.derived_per_pr)

    @property
    def open_issue_net_change(self) -> int:
        """open Issue 純増（窓内作成 − 窓内 close）。"""
        return self.created_issues - self.closed_issues

    def as_dict(self) -> dict[str, object]:
        return {
            "window": self.window.as_dict(),
            "denominator": {"merged_prs": self.merged_prs},
            "primary": {
                "definition": (
                    "窓内に作成された Issue のうち、本文が参照する PR "
                    "（#N 記法・同一リポジトリの OWNER/REPO#N 記法・同一リポジトリの完全 URL の"
                    "3記法を同一の参照として数える）に "
                    "「起票時刻から遡って72時間以内に merge された PR」を"
                    "1つ以上含むもの（派生 Issue）"
                ),
                "derived_issues": self.derived_issues,
                "derived_per_pr": _rounded(self.derived_per_pr),
                "derived_issue_numbers": list(self.derived_issue_numbers),
            },
            "secondary": {
                "definition": "窓内に作成された全 Issue 数（起票粒度の変化に汚染される副指標）",
                "created_issues": self.created_issues,
                "issues_per_pr": _rounded(self.issues_per_pr),
            },
            "open_issue_net_change": {
                "created": self.created_issues,
                "closed": self.closed_issues,
                "net": self.open_issue_net_change,
            },
        }
