"""後段の信頼境界。呼出側の期待値へ完全に束縛する。"""
from .model import normalize

BINDINGS = ("producer", "phase", "issue", "run_id", "target_key", "input_digest",
            "snapshot_oid", "artifact_type", "input_refs")


def validate_handoff(raw, expected):
    data = normalize(raw)
    missing = set(BINDINGS) - set(expected)
    if missing:
        raise ValueError(f"照合期待値が欠落: {sorted(missing)}")
    for key in BINDINGS:
        if data[key] != expected[key]:
            raise ValueError(f"artifact束縛不一致/stale: {key}")
    if (data["status"] != "ready" or data["unresolved_findings"]
            or data["unresolved_owner_decisions"]):
        raise ValueError("STOP/未解消finding/未決owner decision")
    if data["artifact_type"] == "ChangePlan":
        approved = set(expected.get("ac_refs", []))
        covered = {ref for unit in data["work_units"] for ref in unit["ac_refs"]}
        if not approved or covered != approved:
            raise ValueError("AC未対応または未知AC")
    return data
