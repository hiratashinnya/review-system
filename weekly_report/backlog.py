"""Report current backlog and dependency observations separately from events."""

from datetime import timedelta

from .gh_acceptance import acceptance_evidence
from .gh_initiatives import initiatives
from .quantities import count, measured
from .records import public_item

STALE_AFTER = timedelta(days=30)


def _open(data):
    if data["rows"] is None:
        return None
    return [row for row in data["rows"] if row["state"] == "open"]


def measure(observed_at, github):
    issues, pulls = _open(github["issues"]), _open(github["pulls"])
    metrics = {}
    for kind, rows in (("issues", issues), ("pulls", pulls)):
        data = github[kind]
        stale = None if rows is None else [row for row in rows
                                          if row["updated_at"] <= observed_at - STALE_AFTER]
        metrics[f"open_{kind}"] = count(rows, f"観測時に open の {kind}", data)
        metrics[f"stale_{kind}"] = count(stale, f"観測時に最新更新から30日以上の open {kind}", data)
    details = github["blocked_by"]
    blocked = [number for number, data in details.items()
               if any(row["state"] == "open" for row in data["rows"] or [])]
    expected = {row["number"] for row in issues or []}
    unavailable = sorted(number for number in expected
                         if number not in details or details[number]["rows"] is None)
    reason = None
    if issues is None or unavailable:
        reason = "open Issue または依存関係の取得範囲が不完全です"
    metrics["blocked_issues"] = measured(
        None if reason else len(blocked), "観測時に未完了の blocked-by 関係がある open Issue",
        "GitHub REST issues/{number}/dependencies/blocked_by", reason=reason,
        status="not_retrieved" if reason else "measured",
        observed_issue_numbers=blocked, unmeasured_issue_numbers=unavailable,
    )
    return metrics, {
        "open_issues": None if issues is None else [public_item(row) for row in issues],
        "open_pulls": None if pulls is None else [public_item(row) for row in pulls],
        "blocked_by": github["blocked_by"],
        "sub_issues": github["sub_issues"],
        "initiative_progress": initiatives(github["issues"]["rows"], github["sub_issues"]),
        "issue_acceptance": None if github["issues"]["rows"] is None else {
            row["number"]: acceptance_evidence(row) for row in github["issues"]["rows"]
        },
    }
