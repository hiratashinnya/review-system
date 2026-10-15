"""Compatibility exports for defect metric calculation."""

from .aggregation import WindowMetrics, _ratio, _rounded, compute_window_metrics, is_derived
from .model import DERIVATION_HORIZON, RATIO_DIGITS, IssueRecord, PullRequestRecord, Window
from .references import ISSUE_REFERENCE_RE, QUALIFIED_REFERENCE_RE, URL_REFERENCE_RE, _is_measured_repository, normalise_repository, referenced_numbers

__all__ = [
    "DERIVATION_HORIZON",
    "RATIO_DIGITS",
    "IssueRecord",
    "PullRequestRecord",
    "Window",
    "WindowMetrics",
    "ISSUE_REFERENCE_RE",
    "QUALIFIED_REFERENCE_RE",
    "URL_REFERENCE_RE",
    "normalise_repository",
    "referenced_numbers",
    "is_derived",
    "compute_window_metrics",
]
