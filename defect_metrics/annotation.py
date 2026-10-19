"""Render a GitHub warning from the published defect-metrics report."""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


def _window_text(block: dict[str, Any]) -> str:
    window = block["window"]
    primary = block["primary"]
    denominator = block["denominator"]
    return (
        f"[{window['start']}, {window['end']}): "
        f"{primary['derived_issues']}/{denominator['merged_prs']} = "
        f"{primary['derived_per_pr']:.2f} derived issues/merged PRs"
    )


def render_warning(report: dict[str, Any]) -> str:
    """Return one annotation line, or an empty string when alerts are absent."""
    threshold = report["threshold"]
    alerts = threshold["alerts"]
    if not alerts:
        return ""

    current = report["report_window"]
    trailing = report["trailing_4_weeks"]
    current_primary = current["primary"]
    trailing_primary = trailing["primary"]
    codes = {alert["code"] for alert in alerts}
    current_count = current_primary["derived_issues"]
    current_total = current["denominator"]["merged_prs"]
    trailing_count = trailing_primary["derived_issues"]
    trailing_total = trailing["denominator"]["merged_prs"]
    issue_numbers = current_primary["derived_issue_numbers"]
    targets = " ".join(f"#{number}" for number in issue_numbers) or "なし"
    change = "n/a"
    if trailing_total and trailing_count:
        change = f"{float(Fraction(current_count * trailing_total, current_total * trailing_count) - 1):+.2%}"
    elif trailing_total and current_count:
        change = "0から増加"
    elif trailing_total:
        change = "両窓0"
    reasons = "; ".join(f"{item['code']}: {item['detail']}" for item in alerts)
    baseline = "超過" if "BASELINE_EXCEEDED" in codes else "超過なし"
    pooling = trailing["aggregation"]["detail"]
    return (
        f"defect-metrics anomaly ({reasons}); 対象窓 {_window_text(current)}; "
        f"比較窓 {_window_text(trailing)}; 変化 {change}; 対象 Issue {targets}; "
        f"baseline 0.68 は {baseline}。比較窓は28日間のプールド比 ({pooling})。"
        "派生 Issue は本文が同一リポジトリの PR を参照し、起票前72時間以内に merge 済みである"
        "という機械条件による代理指標で、計画タスクを含み、欠陥分類や因果関係は判定しない。"
        "表示比率は丸め値で、判定には既存精度を使う。"
    )


def main() -> int:
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    message = render_warning(report)
    if message:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
