"""Single source for triage phases: which may be proposed, which may ever be auto-applied (#783)."""

# Phases whose findings may be auto-applied; equals policy "enabled_phases" and never grows here.
AUTO_PHASES = ("review", "remediation_review")

# Per proposal phase: reviewer role, reviewed artifact type, Karte review-envelope phase.
# envelope_phase is None where no Karte review envelope exists yet (wiring is #784).
PHASE_ROUTES = {
    "verification_design": {"reviewer": "plan-reviewer", "artifact_type": "VerificationDesign",
                            "envelope_phase": None},
    "solution_planning": {"reviewer": "plan-reviewer", "artifact_type": "ChangePlan",
                          "envelope_phase": None},
    "test_design": {"reviewer": "pr-reviewer", "artifact_type": "TestDesign",
                    "envelope_phase": "test_design"},
    "review": {"reviewer": "pr-reviewer", "artifact_type": "ChangePlan",
               "envelope_phase": "implementation"},
    "remediation_review": {"reviewer": "pr-reviewer", "artifact_type": "ChangePlan",
                           "envelope_phase": "implementation"},
}

# Phases for which a suggestion may be produced; a superset of AUTO_PHASES.
PROPOSAL_PHASES = tuple(PHASE_ROUTES)
