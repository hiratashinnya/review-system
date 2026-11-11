"""Versioned finding-triage input and policy validation (#781)."""

from collections.abc import Mapping

SCHEMA = "triage-policy/v1"
VERSION = "1.0"
OUTCOMES = ("fix-here", "deferred", "advisory")
PHASES = ("review", "remediation_review")
BOOLEANS = (
    "reviewer_verified", "evidence_complete", "ac_relation_verified",
    "reviewer_conflict", "scope_override_requested", "ac_violation",
    "design_violation", "contract_violation", "regression",
    "spec_decision_required", "scope_expansion_required", "preexisting",
    "worsened", "high_risk", "optional_improvement", "handoff_verified",
    "advisory_verified",
)


def validate_policy(policy: object) -> list[str]:
    if not isinstance(policy, dict):
        return ["invalid-policy-object"]
    errors = []
    expected = {"schema", "policy_id", "policy_version", "status", "auto_apply_enabled",
                "enabled_phases", "feature_flags", "rules"}
    if set(policy) != expected:
        errors.append("policy-fields")
    if policy.get("schema") != SCHEMA or policy.get("policy_version") != VERSION:
        errors.append("unknown-policy-version")
    if policy.get("policy_id") != "review-finding-disposition":
        errors.append("unknown-policy-id")
    if policy.get("status") not in ("draft", "approved"):
        errors.append("invalid-policy-status")
    if type(policy.get("auto_apply_enabled")) is not bool:
        errors.append("invalid-policy-enable")
    if policy.get("enabled_phases") != list(PHASES):
        errors.append("invalid-policy-phases")
    flags = policy.get("feature_flags")
    if not isinstance(flags, dict) or set(flags) != set(OUTCOMES) or any(
        type(value) is not bool for value in flags.values()
    ):
        errors.append("invalid-feature-flags")
    rules = policy.get("rules")
    if not isinstance(rules, list) or [r.get("outcome") if isinstance(r, dict) else None
                                       for r in rules] != list(OUTCOMES):
        errors.append("invalid-rule-order")
    else:
        for rule in rules:
            if set(rule) != {"outcome", "all_true", "all_false", "any_true", "equals"}:
                errors.append("invalid-rule-fields")
                continue
            operands = [rule.get(key) for key in ("all_true", "all_false", "any_true")]
            if any(not isinstance(item, list) or any(key not in BOOLEANS for key in item)
                   or len(item) != len(set(item)) for item in operands):
                errors.append("invalid-rule-operands")
            equals = rule.get("equals")
            if not isinstance(equals, dict) or any(
                key not in ("harm", "severity") or not isinstance(value, str)
                for key, value in equals.items()
            ):
                errors.append("invalid-rule-equals")
    return errors


def validate_finding(finding: object) -> list[str]:
    if not isinstance(finding, Mapping):
        return ["invalid-finding-object"]
    errors = []
    for name in BOOLEANS:
        if type(finding.get(name)) is not bool:
            errors.append("missing-or-invalid:" + name)
    enums = {"phase": PHASES, "harm": ("real", "none"),
             "severity": ("blocker", "major", "minor"), "scope": ("in", "out")}
    for name, allowed in enums.items():
        if finding.get(name) not in allowed:
            errors.append("missing-or-invalid:" + name)
    if not isinstance(finding.get("finding_id"), str) or not finding.get("finding_id"):
        errors.append("missing-finding-id")
    if not isinstance(finding.get("policy_ref"), str):
        errors.append("missing-policy-ref")
    return errors
