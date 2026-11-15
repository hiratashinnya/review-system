"""Derived views only: no secondary index or persistent report."""

from datetime import date


def entries(catalog: dict[str, dict], today: str, stale_days: int = 30) -> list[dict]:
    now = date.fromisoformat(today)
    if stale_days < 0:
        raise ValueError("stale days must be nonnegative")
    result = []
    for key, item in sorted(catalog.items()):
        age = (now - date.fromisoformat(item["created_on"])).days
        result.append({
            "id": key, "topic": item["topic"], "status": item["status"],
            "age_days": age, "stale": item["status"] in ("open", "triaged")
            and age >= stale_days, "sources": item["sources"],
            "promoted_issue": item["promoted_issue"],
        })
    return result
