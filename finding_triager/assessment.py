"""Validate independent judgments and derive a conservative policy input."""

from triage_policy.contract import BOOLEANS

EVIDENCE = ("ac", "vd_cp", "design", "change")
FIELDS = set(BOOLEANS) - {"reviewer_verified", "reviewer_conflict", "scope_override_requested"}


def policy_input(review: dict, assessment: dict, phase: str, policy_ref: str) -> dict:
    if not isinstance(assessment, dict) or set(assessment) != {"finding_id", "harm", "scope", "evidence", "facts"}:
        raise ValueError("invalid assessment fields")
    if assessment["finding_id"] != review["finding_id"]:
        raise ValueError("finding mismatch")
    if assessment["harm"] not in ("real", "none") or assessment["scope"] not in ("in", "out"):
        raise ValueError("invalid assessment judgments")
    evidence = assessment["evidence"]
    if not isinstance(evidence, dict) or set(evidence) != set(EVIDENCE):
        raise ValueError("missing evidence categories")
    if any(not isinstance(evidence[k], str) or not evidence[k].strip() for k in EVIDENCE):
        raise ValueError("empty evidence")
    facts = assessment["facts"]
    if not isinstance(facts, dict) or set(facts) != FIELDS:
        raise ValueError("invalid facts")
    if any(type(v) is not bool for v in facts.values()):
        raise ValueError("invalid fact value")
    conflict = assessment["harm"] != review["harm"] or assessment["scope"] != review["scope"]
    return {**facts, "finding_id": review["finding_id"], "phase": phase,
            "policy_ref": policy_ref, "harm": assessment["harm"], "scope": assessment["scope"],
            "severity": review["severity"], "reviewer_verified": True,
            "reviewer_conflict": conflict, "scope_override_requested": assessment["scope"] != review["scope"]}
