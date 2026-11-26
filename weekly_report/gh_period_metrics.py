"""Measure GitHub merge destinations and observable issue lifecycle changes."""

from .gh_issue_history import event_time
from .gh_issue_stock import restore_open
from .quantities import count, measured

CLOSE_TIMING = "最終クローズは Issue の実効時刻、以前のクローズは API の記録時刻"


def merge_destinations(merged, pull_data, repository):
    groups = {"main": [], "other": [], "unknown": []}
    for row in merged or []:
        base = row["base"]
        if not base or row.get("base_repository") != repository.lower():
            groups["unknown"].append(row)
        else:
            groups["main" if base == "main" else "other"].append(row)
    titles = {"main": "main をマージ先とする", "other": "main 以外をマージ先とする", "unknown": "マージ先が不明の"}
    return {
        f"pulls_merged_{key}": count(rows if merged is not None else None,
                                     f"期間内に{titles[key]}マージ済み PR", pull_data)
        for key, rows in groups.items()
    }


def lifecycle(period, issues, created_metric, transition_data):
    rows = [row for row in transition_data.get("known_rows", transition_data["rows"] or [])
            if period.contains(event_time(row))]
    groups = {name: [row for row in rows if row["event"] == name] for name in ("closed", "reopened")}
    count_known = transition_data["rows"] is not None
    source = transition_data["source"]
    reason = transition_data["reason"]
    metrics = {
        f"issues_{name}_events": measured(
            len(groups[event]) if count_known else None, definition, source,
            reason=reason, status="measured" if count_known else "not_retrieved",
            observed_count=len(groups[event]),
        )
        for name, event, definition in (
            ("close", "closed", f"期間内の Issue クローズイベント件数（{CLOSE_TIMING}）"),
            ("reopen", "reopened", "期間内の Issue 再オープンイベント件数"),
        )
    }
    metrics.update(_close_reason_metrics(groups["closed"], source, reason))
    created = created_metric["value"]
    delta = created + len(groups["reopened"]) - len(groups["closed"]) if count_known and created is not None else None
    metrics["issue_backlog_event_delta"] = measured(
        delta, f"期間内の起票 + 再オープンイベント − クローズイベント（{CLOSE_TIMING}）",
        [created_metric["source"], source], reason=reason or created_metric["reason"],
        status="not_retrieved" if delta is None else "measured",
        created=created, known_reopened=len(groups["reopened"]), known_closed=len(groups["closed"]),
    )
    metric, restored, known_restored = restore_open(period, issues, transition_data, CLOSE_TIMING)
    metrics["issues_open_before_cutoff"] = metric
    events = {"issue_transitions": rows if count_known else None, "issues_open_before_cutoff": restored}
    if not count_known:
        events["issue_transitions_known"] = rows
    if known_restored is not None:
        events["issues_open_before_cutoff_known"] = known_restored
    transfers = transition_data.get("transfer_events")
    events["issue_transfers"] = None if transfers is None else [
        row for row in transfers if period.contains(row["created_at"])
    ]
    return metrics, events


def _close_reason_metrics(rows, source, reason):
    definitions = {"completed": "完了", "not_planned": "予定なし", "duplicate": "重複", "unknown": "理由不明"}
    has_unknown = any(row["state_reason"] is None for row in rows)
    metrics = {}
    for key, label in definitions.items():
        matching = [row for row in rows if (row["state_reason"] or "unknown") == key]
        unknown_reason = "理由が不明なクローズが含まれます" if has_unknown and key != "unknown" else None
        metrics[f"issues_close_events_{key}"] = measured(
            None if reason or unknown_reason else len(matching),
            f"期間内の Issue クローズイベントのうち「{label}」（{CLOSE_TIMING}）", source,
            reason=reason or unknown_reason, observed_count=len(matching),
            status="not_retrieved" if reason else "not_measured" if unknown_reason else "measured",
        )
    return metrics
