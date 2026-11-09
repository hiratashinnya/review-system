"""Policy enablement gate; only a trusted adopter may consume the outcome."""

from .evaluator import suggest
from .loader import policy_digest


def evaluate(policy: object, finding: object, approval: object = None) -> dict:
    suggestion = suggest(policy, finding)
    candidate = suggestion["candidate"]
    result = {"candidate": candidate, "disposition": "owner-review",
              "auto_applicable": False, "reason_codes": list(suggestion["reason_codes"])}
    if candidate == "owner-review":
        return result
    if policy["status"] != "approved" or not policy["auto_apply_enabled"]:
        result["reason_codes"].append("policy-not-enabled")
    if not policy["feature_flags"][candidate]:
        result["reason_codes"].append("feature-disabled:" + candidate)
    if not _approved(approval, policy, candidate, finding["phase"]):
        result["reason_codes"].append("owner-approval-not-verified")
    if candidate == "deferred" and not finding["handoff_verified"]:
        result["reason_codes"].append("handoff-not-verified")
    if candidate == "advisory" and not finding["advisory_verified"]:
        result["reason_codes"].append("advisory-not-verified")
    if len(result["reason_codes"]) == 1:
        result["disposition"] = candidate
        result["auto_applicable"] = True
    return result


def _approved(approval: object, policy: dict, candidate: str, phase: str) -> bool:
    """Structured proof supplied only by a trusted owner-approval verifier."""
    if not isinstance(approval, dict) or set(approval) != {
        "verified_by_trusted_cli", "owner", "feedback_ref", "policy_ref",
        "policy_digest", "allowed_dispositions", "allowed_phases",
    }:
        return False
    return (approval["verified_by_trusted_cli"] is True
            and isinstance(approval["owner"], str) and bool(approval["owner"].strip())
            and isinstance(approval["feedback_ref"], str)
            and approval["feedback_ref"].startswith("FBK-")
            and approval["policy_ref"] == policy["policy_id"] + "@" + policy["policy_version"]
            and approval["policy_digest"] == policy_digest(policy)
            and isinstance(approval["allowed_dispositions"], list)
            and candidate in approval["allowed_dispositions"]
            and isinstance(approval["allowed_phases"], list)
            and phase in approval["allowed_phases"])
