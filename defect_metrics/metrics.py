"""窓ごとの指標算出（Issue #488）。

分母・分子の定義は :mod:`defect_metrics.model` の docstring に固定してある。
本モジュールはその定義を実行するだけで、閾値判定は :mod:`defect_metrics.threshold`
が担う（機械判定と運用ルールを混ぜない＝PR2）。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re

from .model import (
    DERIVATION_HORIZON,
    RATIO_DIGITS,
    IssueRecord,
    PullRequestRecord,
    Window,
)

# Issue/PR 本文中の `#N` 参照。
#   - 直前が英数・``_``・``/``・``#``・``&`` の場合は参照とみなさない
#     （``abc#12``／``org/repo#12`` のような他リポジトリ参照、``##`` 見出し、
#     ``&#187;`` のような HTML entity を除外する）。
#   - 直後が英数・``_`` の場合も除外する（``#1abc`` は Issue 番号ではない）。
# 本文以外（タイトル・コメント）は見ない。Issue #488 が「本文が参照する `#N`」と
# 定義しているため、参照元を本文に固定する。
ISSUE_REFERENCE_RE = re.compile(r"(?<![0-9A-Za-z_/#&])#(\d{1,7})(?![0-9A-Za-z_])")


def referenced_numbers(body: str | None) -> set[int]:
    """本文が参照する ``#N`` の集合。"""
    if not body:
        return set()
    return {int(m.group(1)) for m in ISSUE_REFERENCE_RE.finditer(body)}


def _ratio(numerator: int, denominator: int) -> float | None:
    """分母0のとき ``None``（0除算を 0 や inf に潰さず「算出不能」として持ち上げる）。"""
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
        """主指標の厳密値（有理数）。

        float だと ``0.2 * 1.5 == 0.30000000000000004`` のような表現誤差で「ちょうど
        1.5 倍」の境界判定が裏返るため、直近4週との比較（:mod:`defect_metrics.threshold`）は
        この有理数で行う。
        """
        if self.merged_prs == 0:
            return None
        return Fraction(self.derived_issues, self.merged_prs)

    @property
    def derived_per_pr_rounded(self) -> float | None:
        """主指標を表示精度（小数2桁）へ丸めた値。

        基線 0.68 との比較にはこちらを使う——基線定数自体が実測 15/22 = 0.6818… を
        2桁で記録した値であり、厳密値どうしで比べると**基線の窓そのものが「基線超過」に
        なってしまう**（0.6818… > 0.68）。同じ精度で比較して初めて「基線と同じなら異常でない」
        が成立する。
        """
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
                    "窓内に作成された Issue のうち、本文が参照する #N に "
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


def is_derived(
    issue: IssueRecord,
    merged_by_number: dict[int, PullRequestRecord],
) -> bool:
    """``issue`` が派生 Issue か（:mod:`defect_metrics.model` の定義どおり）。

    参照先 PR は**窓の内外を問わない**。窓の先頭直前に merge された PR に由来する
    起票を落とさないため（分子は「窓内に作成された Issue」で絞り、参照先の merge
    時刻は起票時刻からの相対距離だけで判定する）。
    """
    for number in referenced_numbers(issue.body):
        pull = merged_by_number.get(number)
        if pull is None:
            continue
        delta = issue.created_at - pull.merged_at
        # merge が起票より後の PR（後から採番された PR への言及）は原因になりえない。
        if delta.total_seconds() < 0:
            continue
        if delta <= DERIVATION_HORIZON:
            return True
    return False


def compute_window_metrics(
    window: Window,
    issues: list[IssueRecord],
    pulls: list[PullRequestRecord],
) -> WindowMetrics:
    """``window`` に対する指標を算出する。

    ``issues`` / ``pulls`` は窓で絞り込む前の全件を渡す（絞り込みは本関数が行う）。
    """
    merged_by_number = {p.number: p for p in pulls}
    merged_prs = sum(1 for p in pulls if window.contains(p.merged_at))
    created = [i for i in issues if window.contains(i.created_at)]
    closed_issues = sum(1 for i in issues if window.contains(i.closed_at))
    derived = [i for i in created if is_derived(i, merged_by_number)]
    return WindowMetrics(
        window=window,
        merged_prs=merged_prs,
        created_issues=len(created),
        derived_issues=len(derived),
        closed_issues=closed_issues,
        derived_issue_numbers=tuple(sorted(i.number for i in derived)),
    )
