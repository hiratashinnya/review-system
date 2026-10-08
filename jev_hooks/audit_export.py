"""Export anonymous audit fixtures and counters; verdicts remain human supplied."""
import json
import sqlite3
from pathlib import Path


def export(directory):
    database = Path(directory).expanduser() / "state.sqlite3"
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        records = [json.loads(row[0]) for row in connection.execute("SELECT record FROM audit ORDER BY rowid")]
        retained_count = len(records)
        metadata = dict(connection.execute("SELECT name,value FROM audit_metadata"))
        records = [record for record in records if record.get("schema_version") == 1]
        ids = {record["record_id"] for record in records}
        reviews = [{"record_id": rid, "rule": rule, "verdict": verdict}
                   for rid, rule, verdict in connection.execute("SELECT record_id, rule, verdict FROM audit_reviews ORDER BY rowid")
                   if rid in ids]
    return {"schema_version": 1, "records": records, "reviews": reviews,
            "notice_delivery": "not_connected", "coverage": {"retained_records": len(records),
                "total_records": metadata["total_records"], "dropped_records": metadata["total_records"] - retained_count,
                "legacy_records_excluded": retained_count - len(records),
                "retention_records": metadata.get("retention_records"), "window": "retained_records_only",
                "reviews_for_dropped_records": "removed"}}


def counters(fixture):
    result, seen, verdicts = {}, set(), {}
    for review in fixture["reviews"]:
        verdicts[(review["record_id"], review["rule"])] = review["verdict"]
    for record in fixture["records"]:
        if record["request_id"] in seen:
            continue
        seen.add(record["request_id"])
        for rule, outcome in record["outcomes"].items():
            counts = result.setdefault(rule, dict.fromkeys(
                ("evaluations", "candidates", "denials", "unknown", "faults", "reviewed", "positive", "false_positive"), 0))
            counts["evaluations"] += 1
            for field, source in (("candidates", "candidate"), ("denials", "denied"),
                                  ("unknown", "unknown"), ("faults", "fault")):
                counts[field] += bool(outcome[source])
            verdict = verdicts.get((record["record_id"], rule))
            if verdict:
                counts["reviewed"] += 1
                counts[verdict] += 1
    dimensions = {key: sorted({r.get(key, "unknown") for r in fixture["records"]})
                  for key in ("mode", "model", "rule_version", "question_version")}
    return {"schema_version": 1, "unique_requests": len(seen), "rules": result,
            "coverage": fixture.get("coverage", {}), "dimensions": dimensions}


def review(directory, record_id, rule, verdict):
    if rule not in {"R1", "R2", "R3", "R4"} or verdict not in {"positive", "false_positive"}:
        raise ValueError("invalid review")
    database = Path(directory).expanduser() / "state.sqlite3"
    with sqlite3.connect(f"file:{database}?mode=rw", uri=True) as connection:
        records = [json.loads(row[0]) for row in connection.execute("SELECT record FROM audit")]
        if not any(r.get("record_id") == record_id and r.get("outcomes", {}).get(rule, {}).get("candidate") for r in records):
            raise ValueError("review requires existing candidate record")
        connection.execute("INSERT INTO audit_reviews VALUES (?,?,?)", (record_id, rule, verdict))
    return {"record_id": record_id, "rule": rule, "verdict": verdict}
