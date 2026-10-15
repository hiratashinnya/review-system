"""Compatibility exports for defect metric CLI helpers."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from .collect import (
    DEFAULT_FETCH_LIMIT,
    CollectionError,
    fetch_issues,
    fetch_pulls,
    load_issues,
    load_pulls,
    read_json_file,
)
from .cli_baseline import _measured_baseline_values, _mismatches, verify_baseline
from .cli_commands import EXIT_ANOMALY, EXIT_BASELINE_MISMATCH, EXIT_ERROR, EXIT_OK, _cmd_report, _cmd_verify_baseline, main
from .cli_parser import build_parser
from .cli_report import _emit, build_report
from .cli_window import gather, resolve_now, resolve_window
from .metrics import WindowMetrics, compute_window_metrics, normalise_repository
from .model import (
    BASELINE_ALL_ISSUES,
    BASELINE_DERIVED_ISSUES,
    BASELINE_DERIVED_PER_PR,
    BASELINE_ISSUES_PER_PR,
    BASELINE_MERGED_PRS,
    BASELINE_WINDOW,
    DEFAULT_REPORT_WINDOW,
    RATIO_DIGITS,
    SCHEMA_VERSION,
    TRAILING_WINDOW,
    IssueRecord,
    PullRequestRecord,
    Window,
    format_timestamp,
    parse_timestamp,
)
from .threshold import (
    TRAILING_AGGREGATION,
    TRAILING_AGGREGATION_DETAIL,
    Evaluation,
    evaluate,
)

__all__ = [
    "DEFAULT_FETCH_LIMIT",
    "CollectionError",
    "fetch_issues",
    "fetch_pulls",
    "load_issues",
    "load_pulls",
    "read_json_file",
    "WindowMetrics",
    "compute_window_metrics",
    "normalise_repository",
    "BASELINE_ALL_ISSUES",
    "BASELINE_DERIVED_ISSUES",
    "BASELINE_DERIVED_PER_PR",
    "BASELINE_ISSUES_PER_PR",
    "BASELINE_MERGED_PRS",
    "BASELINE_WINDOW",
    "DEFAULT_REPORT_WINDOW",
    "RATIO_DIGITS",
    "SCHEMA_VERSION",
    "TRAILING_WINDOW",
    "IssueRecord",
    "PullRequestRecord",
    "Window",
    "format_timestamp",
    "parse_timestamp",
    "TRAILING_AGGREGATION",
    "TRAILING_AGGREGATION_DETAIL",
    "Evaluation",
    "evaluate",
    "EXIT_OK",
    "EXIT_ERROR",
    "EXIT_ANOMALY",
    "EXIT_BASELINE_MISMATCH",
    "resolve_now",
    "resolve_window",
    "gather",
    "verify_baseline",
    "build_report",
    "build_parser",
    "main",
]
