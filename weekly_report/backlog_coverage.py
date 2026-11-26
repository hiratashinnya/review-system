"""Qualify inventory observations when the surrounding GitHub reads disagree."""

_STATE_FIELDS = {
    "issues": ("open_issues", "blocked_by", "sub_issues", "initiative_progress", "issue_acceptance"),
    "pulls": ("open_pulls",),
}


def apply_consistency(metrics, inventory, consistency):
    if not consistency:
        return metrics, inventory
    metrics, inventory = dict(metrics), dict(inventory)
    coverage = dict(inventory.get("state_coverage") or {})
    for kind, fields in _STATE_FIELDS.items():
        source = consistency.get(kind)
        if not source or source["status"] not in ("changed", "unknown"):
            continue
        absent = source["status"] == "unknown"
        entity = "Issue" if kind == "issues" else "PR"
        status = "not_retrieved" if absent else "not_measured"
        detail = "取得範囲を確認できません" if absent else "変化を検出しました"
        reason = f"{entity} 一覧の前後照合で{detail}"
        if source.get("reason"):
            reason += f'（{source["reason"]}）'
        coverage[kind] = {"status": status, "reason": reason, "source": source["source"]}
        keys = [f"open_{kind}", f"stale_{kind}"]
        if kind == "issues":
            keys.append("blocked_issues")
        for key in keys:
            if key in metrics:
                metrics[key] = {**metrics[key], "value": None, "status": status, "reason": reason}
        if kind == "issues" and "blocked_issues" in metrics:
            metrics["blocked_issues"]["observed_issue_numbers"] = None
        for key in fields:
            inventory[key] = None
    if coverage:
        inventory["state_coverage"] = coverage
    return metrics, inventory
