"""Calculate derived issue counts and metrics for a window."""

from __future__ import annotations

from .metric_values import WindowMetrics
from .model import DERIVATION_HORIZON, IssueRecord, PullRequestRecord, Window
from .references import referenced_numbers


def is_derived(
    issue: IssueRecord,
    merged_by_number: dict[int, PullRequestRecord],
    repository: str,
) -> bool:
    """``issue`` が派生 Issue か（:mod:`defect_metrics.model` の定義どおり）。"""
    for number in referenced_numbers(issue.body, repository):
        pull = merged_by_number.get(number)
        if pull is None:
            continue
        delta = issue.created_at - pull.merged_at
        if delta.total_seconds() < 0:
            continue
        if delta <= DERIVATION_HORIZON:
            return True
    return False


def compute_window_metrics(
    window: Window,
    issues: list[IssueRecord],
    pulls: list[PullRequestRecord],
    repository: str,
) -> WindowMetrics:
    """``window`` に対する指標を算出する。"""
    merged_by_number = {pull.number: pull for pull in pulls}
    merged_prs = sum(1 for pull in pulls if window.contains(pull.merged_at))
    created = [issue for issue in issues if window.contains(issue.created_at)]
    closed_issues = sum(1 for issue in issues if window.contains(issue.closed_at))
    derived = [issue for issue in created if is_derived(issue, merged_by_number, repository)]
    return WindowMetrics(
        window=window,
        merged_prs=merged_prs,
        created_issues=len(created),
        derived_issues=len(derived),
        closed_issues=closed_issues,
        derived_issue_numbers=tuple(sorted(issue.number for issue in derived)),
    )
