"""Build and emit the defect metrics report."""

from __future__ import annotations
import json
from datetime import datetime
from .cli_baseline import verify_baseline
from .metrics import WindowMetrics, compute_window_metrics
from .model import BASELINE_ALL_ISSUES, BASELINE_DERIVED_ISSUES, BASELINE_DERIVED_PER_PR, BASELINE_ISSUES_PER_PR, BASELINE_MERGED_PRS, BASELINE_WINDOW, SCHEMA_VERSION, TRAILING_WINDOW, Window, format_timestamp, IssueRecord, PullRequestRecord
from .threshold import TRAILING_AGGREGATION, TRAILING_AGGREGATION_DETAIL, Evaluation, evaluate


def build_report(
    repository: str,
    window: Window,
    issues: list[IssueRecord],
    pulls: list[PullRequestRecord],
    now: datetime,
) -> tuple[dict[str, object], Evaluation]:
    """レポート JSON と閾値判定結果を作る。"""
    current = compute_window_metrics(window, issues, pulls, repository)
    trailing_window = window.shifted_back(TRAILING_WINDOW)
    trailing = compute_window_metrics(trailing_window, issues, pulls, repository)
    evaluation = evaluate(current, trailing)
    verification, _ = verify_baseline(issues, pulls, repository)

    trailing_block = dict(trailing.as_dict())
    # フィールド名 `trailing_4_weeks` だけでは「プールド比」か「週次比の平均」か読めないため、
    # 集計方法を値として同梱する（Issue #488 F-488-03・根拠は defect_metrics/README.md §3）。
    trailing_block["aggregation"] = {
        "method": TRAILING_AGGREGATION,
        "detail": TRAILING_AGGREGATION_DETAIL,
    }

    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "tool": "defect_metrics",
        "issue": 488,
        "repository": repository,
        "generated_at": format_timestamp(now),
        "report_window": current.as_dict(),
        "trailing_4_weeks": trailing_block,
        "baseline": {
            "source": "Issue #368「現状と根拠」（2026-09-06 訂正）／Issue #488「現状と根拠」",
            "window": BASELINE_WINDOW.as_dict(),
            "merged_prs": BASELINE_MERGED_PRS,
            "created_issues": BASELINE_ALL_ISSUES,
            "issues_per_pr": BASELINE_ISSUES_PER_PR,
            "derived_issues": BASELINE_DERIVED_ISSUES,
            "derived_per_pr": BASELINE_DERIVED_PER_PR,
        },
        "baseline_verification": verification,
        "threshold": evaluation.as_dict(),
    }
    return report, evaluation


def _emit(report: dict[str, object], output: str | None, stdout) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        stdout.write(text)
