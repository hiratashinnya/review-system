"""Compare GitHub list observations that bracket detailed reads."""


def compare_reads(before, after):
    source = [before["source"], after["source"]]
    if before["rows"] is None or after["rows"] is None:
        return {"status": "unknown", "source": source, "changed": None,
                "reason": before["reason"] or after["reason"]}
    first = {row["number"]: row for row in before["rows"]}
    last = {row["number"]: row for row in after["rows"]}
    changes = []
    for number in sorted(first.keys() | last.keys()):
        if number not in first or number not in last:
            changes.append({"number": number, "kind": "added" if number in last else "missing", "fields": []})
            continue
        before_row, after_row = first[number], last[number]
        fields = sorted(key for key in before_row.keys() | after_row.keys()
                        if before_row.get(key) != after_row.get(key))
        if fields:
            change = {"number": number, "kind": "updated", "fields": fields}
            if "head_sha" in fields:
                change.update(before_head_sha=before_row.get("head_sha"), after_head_sha=after_row.get("head_sha"))
            changes.append(change)
    return {"status": "changed" if changes else "unchanged", "source": source, "changed": changes,
            "reason": "取得中の一覧に変化があります" if changes else None}


def pull_observation_reason(consistency, number, *, include_base_sha=False):
    """Require that the same PR and its head survived both list reads."""
    if consistency["status"] == "unknown":
        return "取得の前後で PR を確認できません"
    fields = {"id", "base", "base_repo_id", "head_sha", "state", "merged_at"}
    if include_base_sha:
        fields.add("base_sha")
    for change in consistency["changed"]:
        if change["number"] == number and (
            change["kind"] != "updated"
            or fields.intersection(change["fields"])
        ):
            return "取得中に PR の比較に必要な識別子または状態が変化しました"
    return None
