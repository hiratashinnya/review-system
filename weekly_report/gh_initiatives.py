"""Preserve observed child membership and typed completion evidence."""


def initiatives(issues, children):
    if issues is None:
        return None
    return {
        issue["number"]: _initiative(issue, children.get(issue["number"]))
        for issue in issues if issue["number"] in children
        or (issue.get("sub_issues_summary") or {}).get("total") is not None
    }


def _initiative(issue, child_source):
    number = issue["number"]
    report = {
        "number": number, "title": issue["title"],
        "source": f"GitHub REST issues/{number}/sub_issues",
        "total": None, "completed": None, "closed": None, "open": None,
        "other_closed": None, "unknown_closed": None, "children": None,
    }
    rows = child_source["rows"] if child_source else None
    summary = issue.get("sub_issues_summary") or {}
    listed_total = summary.get("total")
    if rows is None and child_source is None and type(listed_total) is int and listed_total == 0:
        report["source"] = "GitHub REST issues sub_issues_summary.total"
        rows = []
    if rows is None:
        return {**report, "reason": child_source["reason"] if child_source else "子 Issue 一覧の証跡がありません"}
    if type(listed_total) is not int or listed_total != len(rows):
        return {**report, "listed_total": listed_total, "known_children": rows,
                "reason": "親 Issue の分母と子 Issue 一覧の取得件数が一致しません"}
    completed, closed, other_closed, unknown_closed = 0, 0, 0, 0
    for child in rows:
        if child["state"] != "closed":
            continue
        closed += 1
        if child["reason"] == "completed":
            completed += 1
        elif child["reason"] in ("not_planned", "duplicate"):
            other_closed += 1
        else:
            unknown_closed += 1
    return {**report, "total": len(rows), "completed": None if unknown_closed else completed, "closed": closed,
            "open": len(rows) - closed, "other_closed": other_closed, "unknown_closed": unknown_closed,
            "known_completed": completed, "children": rows,
            "reason": "完了理由を確定できない子 Issue があります" if unknown_closed else None}
