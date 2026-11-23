"""Single source for the evidence categories each triage phase must supply (#783)."""

from .phases import route_of

CATEGORIES = ("ac", "vd_cp", "design", "change")
PULL_REQUEST_DIFF = "pull-request-diff"
ARTIFACT_DIFF = "reviewed-artifact-diff"

# A verification-design review has no ChangePlan yet, so it has no design category to supply.
PHASE_EVIDENCE = {
    "verification_design": ("ac", "vd_cp", "change"),
    "solution_planning": CATEGORIES,
    "test_design": CATEGORIES,
    "review": CATEGORIES,
    "remediation_review": CATEGORIES,
}

# What the change category holds: the PR diff for implementation reviews, else the reviewed artifact's diff.
CHANGE_SOURCE = {
    "verification_design": ARTIFACT_DIFF,
    "solution_planning": ARTIFACT_DIFF,
    "test_design": ARTIFACT_DIFF,
    "review": PULL_REQUEST_DIFF,
    "remediation_review": PULL_REQUEST_DIFF,
}


def required_categories(phase: object) -> tuple[str, ...]:
    route_of(phase)
    return PHASE_EVIDENCE[phase]
