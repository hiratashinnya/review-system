"""Single source for triage phases: which may be proposed, which may ever be auto-applied (#783)."""

# Phases whose findings may be auto-applied; equals policy "enabled_phases" and never grows here.
AUTO_PHASES = ("review", "remediation_review")

# reviewer/artifact_type: who reviewed what. envelope_phase: Karte envelope (None until #784 wires it).
# prior: phases whose clean review receipts the approval must hold. reviewed: key of the reviewed artifact.
PHASE_ROUTES = {
    "verification_design": {"reviewer": "plan-reviewer", "artifact_type": "VerificationDesign",
                            "envelope_phase": None, "prior": (), "reviewed": "verification_design"},
    "solution_planning": {"reviewer": "plan-reviewer", "artifact_type": "ChangePlan",
                          "envelope_phase": None, "prior": ("verification_design",),
                          "reviewed": "solution_planning"},
    "test_design": {"reviewer": "pr-reviewer", "artifact_type": "TestDesign",
                    "envelope_phase": "test_design",
                    "prior": ("verification_design", "solution_planning"), "reviewed": "test_design"},
    "review": {"reviewer": "pr-reviewer", "artifact_type": "ChangePlan",
               "envelope_phase": "implementation",
               "prior": ("verification_design", "solution_planning"), "reviewed": "solution_planning"},
    "remediation_review": {"reviewer": "pr-reviewer", "artifact_type": "ChangePlan",
                           "envelope_phase": "implementation",
                           "prior": ("verification_design", "solution_planning"),
                           "reviewed": "solution_planning"},
}

# Phases for which a suggestion may be produced; a superset of AUTO_PHASES.
PROPOSAL_PHASES = tuple(PHASE_ROUTES)


def route_of(phase: object) -> dict:
    """Return the route for a known phase; any other value (even unhashable) is rejected."""
    if not isinstance(phase, str) or phase not in PHASE_ROUTES:
        raise ValueError("unknown triage phase")
    return PHASE_ROUTES[phase]
