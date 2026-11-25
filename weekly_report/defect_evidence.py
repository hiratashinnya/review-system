"""Measure and preserve the defect_metrics inputs for the observed window."""

from defect_metrics.collect import load_issues, load_pulls
from defect_metrics.metrics import compute_window_metrics
from defect_metrics.model import DERIVATION_HORIZON, Window

from .period import NO_OBSERVED_TIME
from .quantities import measured


def inputs(period, issues, pulls):
    if issues is None or pulls is None or period.cutoff == period.start:
        return None
    earliest_merge = period.start - DERIVATION_HORIZON
    return {
        "issues": [
            {"number": row["number"], "createdAt": row["created_at"].isoformat(),
             "closedAt": row["closed_at"].isoformat() if row["closed_at"] is not None else None,
             "body": row["body"]}
            for row in issues if period.contains(row["created_at"]) or period.contains(row["closed_at"])
        ],
        "pulls": [
            {"number": row["number"], "mergedAt": row["merged_at"].isoformat()}
            for row in pulls if row["merged_at"] is not None and earliest_merge <= row["merged_at"] < period.cutoff
        ],
    }


def measure(period, repository, captured, issue_data, pull_data):
    source = {"definition": "defect_metrics/README.md", "inputs": [issue_data["source"], pull_data["source"]],
              "saved_inputs": "snapshot.json#/evidence/defect_metrics"}
    if captured is None:
        reason = (NO_OBSERVED_TIME if period.cutoff == period.start else "Issue または PR の全件を取得できません")
        return measured(None, "defect_metrics の窓内派生 Issue / 窓内マージ PR", source, reason=reason)
    result = compute_window_metrics(Window(period.start, period.cutoff), load_issues(captured["issues"]),
                                    load_pulls(captured["pulls"]), repository)
    primary = result.as_dict()["primary"]
    assert isinstance(primary, dict)
    return measured(
        result.derived_per_pr, primary["definition"], source,
        reason="分母のマージ PR が0件" if result.merged_prs == 0 else None,
        numerator=result.derived_issues, denominator=result.merged_prs,
        derived_issue_numbers=list(result.derived_issue_numbers),
    )
