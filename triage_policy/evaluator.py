"""Deterministic, read-only suggested disposition; no owner decisions are made here."""

from .contract import OUTCOMES, validate_finding, validate_policy

MANDATORY = ("ac_violation", "design_violation", "contract_violation", "regression")


def _matches(rule: dict, finding: dict) -> bool:
    return (all(finding[key] for key in rule["all_true"])
            and all(not finding[key] for key in rule["all_false"])
            and (not rule["any_true"] or any(finding[key] for key in rule["any_true"]))
            and all(finding.get(key) == value for key, value in rule["equals"].items()))


def suggest(policy: object, finding: object) -> dict:
    """Find a candidate only; malformed/uncertain/contradictory input fails closed."""
    errors = validate_policy(policy) + validate_finding(finding)
    if errors:
        return {"candidate": "owner-review", "reason_codes": sorted(set(errors))}
    if finding["policy_ref"] != policy["policy_id"] + "@" + policy["policy_version"]:
        return {"candidate": "owner-review", "reason_codes": ["policy-ref-mismatch"]}
    if not (finding["reviewer_verified"] and finding["evidence_complete"]
            and finding["ac_relation_verified"]):
        return {"candidate": "owner-review", "reason_codes": ["unverified-evidence"]}
    if (finding["reviewer_conflict"] or finding["scope_override_requested"]
            or finding["high_risk"] or finding["spec_decision_required"]
            or finding["scope_expansion_required"]):
        return {"candidate": "owner-review", "reason_codes": ["owner-judgment-required"]}
    if finding["harm"] == "none" and any(finding[key] for key in MANDATORY):
        return {"candidate": "owner-review", "reason_codes": ["harm-contradicts-mandatory"]}
    for rule in policy["rules"]:
        if not _matches(rule, finding):
            continue
        candidate = rule["outcome"]
        if candidate == "fix-here" and not any(finding[key] for key in MANDATORY):
            continue
        if candidate == "deferred" and not _safe_deferred(finding):
            continue
        if candidate == "advisory" and not _safe_advisory(finding):
            continue
        if candidate in OUTCOMES:
            return {"candidate": candidate, "reason_codes": ["rule:" + candidate]}
    return {"candidate": "owner-review", "reason_codes": ["no-safe-rule"]}


def _safe_deferred(finding: dict) -> bool:
    return (finding["preexisting"] and not finding["worsened"]
            and finding["severity"] == "minor"
            and not any(finding[key] for key in MANDATORY))


def _safe_advisory(finding: dict) -> bool:
    return (finding["harm"] == "none" and finding["optional_improvement"]
            and not any(finding[key] for key in MANDATORY))
