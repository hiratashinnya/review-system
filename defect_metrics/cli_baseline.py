"""Recompute and verify the recorded metric baseline."""

from __future__ import annotations
from .metrics import WindowMetrics, compute_window_metrics
from .model import BASELINE_ALL_ISSUES, BASELINE_DERIVED_ISSUES, BASELINE_DERIVED_PER_PR, BASELINE_ISSUES_PER_PR, BASELINE_MERGED_PRS, BASELINE_WINDOW, RATIO_DIGITS, IssueRecord, PullRequestRecord


def _measured_baseline_values(metrics: WindowMetrics) -> dict[str, object]:
    """基線と突き合わせる5つの実測値（比率は基線定数と同じ表示精度へ丸める）。"""
    return {
        "merged_prs": metrics.merged_prs,
        "created_issues": metrics.created_issues,
        "derived_issues": metrics.derived_issues,
        "issues_per_pr": (
            None if metrics.issues_per_pr is None else round(metrics.issues_per_pr, RATIO_DIGITS)
        ),
        "derived_per_pr": (
            None if metrics.derived_per_pr is None else round(metrics.derived_per_pr, RATIO_DIGITS)
        ),
    }


def _mismatches(metrics: WindowMetrics) -> list[str]:
    """基線窓の実測値が記録済み基線と食い違う項目を列挙する（一致すれば空）。"""
    measured = _measured_baseline_values(metrics)
    expected = {
        "merged_prs": BASELINE_MERGED_PRS,
        "created_issues": BASELINE_ALL_ISSUES,
        "derived_issues": BASELINE_DERIVED_ISSUES,
        "issues_per_pr": BASELINE_ISSUES_PER_PR,
        "derived_per_pr": BASELINE_DERIVED_PER_PR,
    }
    return [
        f"{name}: expected {want}, got {measured[name]}"
        for name, want in expected.items()
        if want != measured[name]
    ]


def verify_baseline(
    issues: list[IssueRecord],
    pulls: list[PullRequestRecord],
    repository: str,
) -> tuple[dict[str, object], list[str]]:
    """基線窓を再計測し、記録済み基線と照合した結果を機械可読な形で返す。

    戻り値の第1要素は ``report.json`` の ``baseline_verification`` および
    ``verify-baseline`` の stdout に載せる dict、第2要素は不一致の一覧である。

    **この結果をレポートに載せる理由**（Issue #488 F-488-01(b)）: 照合を Actions の step
    ログにしか残さないと、既定 90 日で失効し、レポートを読む側（#461 の報告経路）へは
    一切届かない。閾値超過が ``threshold.anomaly`` として永続化される一方で基線検証だけが
    揮発するという非対称は、「散文定義による再現不能」という Issue #488 が解こうとした問題の
    再発を、誰にも気づかれないまま許すことになる。
    """
    metrics = compute_window_metrics(BASELINE_WINDOW, issues, pulls, repository)
    mismatches = _mismatches(metrics)
    payload: dict[str, object] = {
        "baseline_window": BASELINE_WINDOW.as_dict(),
        "recorded": {
            "merged_prs": BASELINE_MERGED_PRS,
            "created_issues": BASELINE_ALL_ISSUES,
            "derived_issues": BASELINE_DERIVED_ISSUES,
            "issues_per_pr": BASELINE_ISSUES_PER_PR,
            "derived_per_pr": BASELINE_DERIVED_PER_PR,
        },
        "measured": _measured_baseline_values(metrics),
        "reproduced": not mismatches,
        "mismatches": mismatches,
    }
    return payload, mismatches
