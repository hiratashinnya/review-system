"""Recompute and verify a proposal against its signed review and trusted bindings."""

from .adapter import propose


def validate_proposal(artifact, raw, signature, key, expected):
    if not isinstance(artifact, dict) or not isinstance(artifact.get("proposals"), list):
        raise ValueError("invalid triage artifact")
    assessments = []
    for item in artifact["proposals"]:
        if not isinstance(item, dict) or "triager" not in item:
            raise ValueError("invalid triage proposal")
        assessments.append(item["triager"])
    canonical = propose(raw, signature, key, expected, assessments)
    if artifact != canonical:
        raise ValueError("triage artifact mismatch")
    return canonical
