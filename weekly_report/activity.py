"""Measure period activity from GitHub's latest issue and pull records."""

from statistics import median

from . import defect_evidence
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
    defect_inputs = defect_evidence.inputs(period, issue_data["rows"], pull_data["rows"])
    metrics = {
        "issues_created": count(created, "期間内に起票された Issue", issue_data),
        "pulls_merged": count(merged, "期間内にマージされた PR（全 base）", pull_data),
        "pull_lead_days": _lead(merged, "merged_at", "期間内マージ PR の起票からマージまでの中央値", pull_data),
        "defects_per_merge": defect_evidence.measure(period, repository, defect_inputs, issue_data, pull_data),
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
    if missing_timestamp:
        events["closed_known"], events["closed"] = events["closed"], None
    return metrics, events, defect_inputs
