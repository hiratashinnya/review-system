"""Owner-facing, non-executable PR blocker report envelope."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping


REPORT_SCHEMA = "owner-pr-blocker-report/1"


def build_owner_report(
    repository: str, number: int, method: str, evidence: Mapping[str, Any]
) -> dict[str, Any]:
    """Package blocker evidence while keeping the merge decision with the owner."""
    verdict = evidence.get("result")
    if verdict not in {"ALLOW", "BLOCK", "ERROR"}:
        raise ValueError("invalid blocker verdict")
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": repository,
        "pull_request": number,
        "merge_method": method,
        "verdict": verdict,
        "reason": evidence.get("primary_reason"),
        "owner_action_required": True,
        "automatic_merge_authorized": False,
        "merge_api_called": False,
        "next_action": "OWNER_REVIEW_REPORT" if verdict == "ALLOW" else "DO_NOT_MERGE",
        "blocker_evidence": deepcopy(dict(evidence)),
    }
