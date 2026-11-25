"""Measure period activity from GitHub's latest issue and pull records."""

from statistics import median

from defect_metrics.metrics import compute_window_metrics
from defect_metrics.model import IssueRecord, PullRequestRecord, Window

from .quantities import count, measured
from .records import public_item

LATEST_CLOSE = "最新 closed_at が期間内にある現在閉じた Issue。過去の close/reopen は対象外。"


def _select(source, predicate):
    rows = source["rows"]
    return None if rows is None else [row for row in rows if predicate(row)]


def _lead(rows, field, definition, dataset, reason=None):
    days = [(row[field] - row["created_at"]).total_seconds() / 86400 for row in rows or []]
    sample = None if rows is None or reason else len(days)
    return measured(
        median(days) if sample else None, definition, dataset["source"], n=sample,
        unit="日", reason=reason or dataset["reason"] or ("対象が0件" if not days else None),
    )


def _close_reason(item):
    return item["state_reason"] if item["state_reason"] in ("completed", "not_planned", "duplicate") else "unknown"


def measure(period, repository, issue_data, pull_data):
    created = _select(issue_data, lambda row: period.contains(row["created_at"]))
    closed = _select(issue_data, lambda row: row["state"] == "closed" and period.contains(row["closed_at"]))
    merged = _select(pull_data, lambda row: period.contains(row["merged_at"]))
    metrics = {
        "issues_created": count(created, "期間内に起票された Issue", issue_data),
        "pulls_merged": count(merged, "期間内にマージされた PR（全 base）", pull_data),
        "pull_lead_days": _lead(merged, "merged_at", "期間内マージ PR の起票からマージまでの中央値", pull_data),
        "defects_per_merge": _defects(period, repository, issue_data, pull_data),
    }
    close_groups = {key: None if closed is None else [row for row in closed if _close_reason(row) == key]
                    for key in ("completed", "not_planned", "duplicate", "unknown")}
    complete = close_groups["completed"]
    unknown = "理由不明のクローズがあり、完了数を確定できません" if close_groups["unknown"] else None
    missing_timestamp = any(row["state"] == "closed" and row["closed_at"] is None
                            for row in issue_data["rows"] or [])
    if missing_timestamp:
        unknown = "クローズ時刻の欠損があり、期間内の件数を確定できません"
    for key, rows in close_groups.items():
        metric = count(rows, f"{LATEST_CLOSE} state_reason={key}", issue_data)
        if rows is not None and (missing_timestamp or (key == "completed" and unknown)):
            metric |= {"value": None, "reason": unknown, "observed_count": len(rows)}
        metrics[f"issues_closed_{key}"] = metric
    metrics["issue_lead_days"] = _lead(
        complete, "closed_at", "最新の completed Issue の起票からクローズまでの中央値",
        issue_data, unknown,
    )
    events = {key: None if rows is None else [public_item(row) for row in rows]
              for key, rows in {"created": created, "closed": closed, "merged": merged}.items()}
    return metrics, events


def _defects(period, repository, issues, pulls):
    from defect_metrics.metric_values import WindowMetrics

    definition = "defect_metrics の窓内派生 Issue / 窓内マージ PR"
    source = {"definition": "defect_metrics/README.md", "inputs": [issues["source"], pulls["source"]]}
    if issues["rows"] is None or pulls["rows"] is None:
        return measured(None, definition, source, reason="Issue または PR の全件を取得できません")
    if period.cutoff == period.start:
        return measured(None, definition, source, reason="観測済みの時間帯がありません", n=0)
    result: WindowMetrics = compute_window_metrics(
        Window(period.start, period.cutoff),
        [IssueRecord(row["number"], row["created_at"], row["closed_at"], row["body"] or "")
         for row in issues["rows"]],
        [PullRequestRecord(row["number"], row["merged_at"]) for row in pulls["rows"] if row["merged_at"]],
        repository,
    )
    primary = result.as_dict()["primary"]
    assert isinstance(primary, dict)
    return measured(
        result.derived_per_pr, primary["definition"], source,
        reason="分母のマージ PR が0件" if result.merged_prs == 0 else None,
        numerator=result.derived_issues, denominator=result.merged_prs,
        derived_issue_numbers=list(result.derived_issue_numbers),
    )
