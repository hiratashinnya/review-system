"""Issue #783 F-783-06: five proposal phases, auto-apply stays at two."""

import copy
import hashlib
import hmac
import json
from pathlib import Path
import unittest

from codex_worktree_exec.artifact_binding import INPUT_KINDS
from codex_worktree_exec.review_binding import PHASE_BY_INPUT
from finding_triager import inputs
from triage_policy import evaluate, load_policy, policy_digest, suggest
from triage_policy.contract import validate_finding, validate_policy
from triage_policy.phases import AUTO_PHASES, PHASE_ROUTES, PROPOSAL_PHASES
from tests.unit.test_triage_policy import approval, evidence

ROOT = Path(__file__).resolve().parents[2]
# Digest of policy 1.1 as of F-783-06; widening auto-apply later must change this on purpose.
POLICY_DIGEST = "4483bab3bf08628327313e3a4cbba124836c69cd1c56669f992ab569ff39f096"
PROPOSAL_ONLY = ("verification_design", "solution_planning", "test_design")


def schema(name):
    return json.loads((ROOT / ".ai" / "schema" / name).read_text(encoding="utf-8"))


class PhaseConstantsTest(unittest.TestCase):
    def test_auto_phases_are_the_two_existing_ones(self):
        self.assertEqual(AUTO_PHASES, ("review", "remediation_review"))
        self.assertEqual(set(PROPOSAL_PHASES) - set(AUTO_PHASES), set(PROPOSAL_ONLY))
        self.assertEqual(set(PROPOSAL_PHASES), set(PHASE_ROUTES))

    def test_unknown_phase_rejected_in_every_form(self):
        for phase in ("planning", "", None, 1, ["review"], "Review"):
            with self.subTest(phase=phase):
                self.assertIn("missing-or-invalid:phase", validate_finding(evidence(phase=phase)))

    def test_route_table_matches_existing_reviewer_tables(self):
        for phase, route in PHASE_ROUTES.items():
            with self.subTest(phase=phase):
                self.assertIn(route["artifact_type"], INPUT_KINDS[route["reviewer"]])
                if route["envelope_phase"] is not None:
                    self.assertEqual(PHASE_BY_INPUT[route["artifact_type"]], route["envelope_phase"])
        self.assertEqual({r["reviewer"] for p, r in PHASE_ROUTES.items() if p in PROPOSAL_ONLY[:2]},
                         {"plan-reviewer"})

    def test_inputs_no_longer_duplicates_phase_constant(self):
        self.assertFalse(hasattr(inputs, "PHASES"))


class PolicyAndSchemaUnchangedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()

    def test_policy_values_and_digest_are_pinned(self):
        policy = self.policy
        self.assertEqual(policy["enabled_phases"], ["review", "remediation_review"])
        self.assertEqual((policy["policy_version"], policy["status"], policy["auto_apply_enabled"]),
                         ("1.1", "draft", False))
        self.assertEqual(policy["feature_flags"], {"fix-here": False, "deferred": False, "advisory": False})
        self.assertEqual(policy_digest(policy), POLICY_DIGEST)

    def test_policy_enabled_phases_cannot_be_widened(self):
        widened = copy.deepcopy(self.policy)
        widened["enabled_phases"] = list(PROPOSAL_PHASES)
        self.assertIn("invalid-policy-phases", validate_policy(widened))

    def test_schemas_agree_with_constants(self):
        policy_schema = schema("triage-policy-v1.json")
        props = policy_schema["properties"]
        self.assertEqual(props["enabled_phases"]["const"], list(AUTO_PHASES))
        defs = policy_schema["$defs"]
        self.assertEqual(defs["owner_approval"]["properties"]["allowed_phases"]["items"]["enum"],
                         list(AUTO_PHASES))
        self.assertEqual(defs["finding_evidence"]["properties"]["phase"]["enum"], list(PROPOSAL_PHASES))
        artifact = schema("finding-triage-v1.json")
        self.assertEqual(artifact["properties"]["phase"]["enum"], list(PROPOSAL_PHASES))
        self.assertEqual(artifact["properties"]["policy_version"]["const"], self.policy["policy_version"])
        self.assertEqual(artifact["properties"]["schema"]["const"], "finding-triage/v1")


class ProposalAndAutoApplyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()

    def test_all_five_phases_validate_and_suggest(self):
        for phase in PROPOSAL_PHASES:
            with self.subTest(phase=phase):
                self.assertEqual(validate_finding(evidence(phase=phase)), [])
                self.assertEqual(suggest(self.policy, evidence(phase=phase, ac_violation=True)),
                                 {"candidate": "fix-here", "reason_codes": ["rule:fix-here"]})

    def enabled(self):
        policy = copy.deepcopy(self.policy)
        policy.update(status="approved", auto_apply_enabled=True)
        policy["feature_flags"] = dict.fromkeys(policy["feature_flags"], True)
        return policy

    def test_auto_phases_still_auto_applicable_when_fully_enabled(self):
        policy = self.enabled()
        for phase in AUTO_PHASES:
            with self.subTest(phase=phase):
                result = evaluate(policy, evidence(phase=phase, ac_violation=True), approval(policy),
                                  verify_owner=lambda proof, digest: True)
                self.assertTrue(result["auto_applicable"])
                self.assertEqual(result["disposition"], "fix-here")

    def test_proposal_only_phases_never_auto_apply_even_fully_enabled(self):
        policy = self.enabled()
        every_phase = approval(policy, allowed_phases=list(PROPOSAL_PHASES))
        for phase in PROPOSAL_ONLY:
            for proof in (approval(policy), every_phase):
                with self.subTest(phase=phase, allowed=proof["allowed_phases"]):
                    result = evaluate(policy, evidence(phase=phase, ac_violation=True), proof,
                                      verify_owner=lambda p, digest: True)
                    self.assertFalse(result["auto_applicable"])
                    self.assertEqual(result["disposition"], "owner-review")
                    self.assertEqual(result["candidate"], "fix-here")
                    self.assertIn("phase-not-auto-enabled", result["reason_codes"])

    def test_approval_naming_a_proposal_only_phase_is_rejected_for_every_phase(self):
        policy = self.enabled()
        proof = approval(policy, allowed_phases=["review", "test_design"])
        result = evaluate(policy, evidence(ac_violation=True), proof, verify_owner=lambda p, d: True)
        self.assertFalse(result["auto_applicable"])
        self.assertIn("owner-approval-not-verified", result["reason_codes"])


def signed_review(phase, producer):
    expected = {"issue": 783, "phase": phase, "round": 1, "run_id": "r", "target_key": "k",
                "input_digest": "a" * 64, "snapshot_oid": "b" * 40, "review_oid": "c" * 40}
    data = dict(expected, producer=producer, findings=[], reviewer_worktree="/reviewer",
                context_sha256="d" * 64)
    raw = json.dumps(data).encode()
    key = b"k" * 32
    return raw, hmac.new(key, raw, hashlib.sha256).hexdigest(), key, expected


class VerifyReviewPhaseTest(unittest.TestCase):
    def test_each_phase_accepts_only_its_reviewer(self):
        for phase, route in PHASE_ROUTES.items():
            for producer in ("pr-reviewer", "plan-reviewer"):
                raw, signature, key, expected = signed_review(phase, producer)
                with self.subTest(phase=phase, producer=producer):
                    if producer == route["reviewer"]:
                        self.assertEqual(inputs.verify_review(raw, signature, key, expected)["phase"], phase)
                    else:
                        with self.assertRaises(ValueError):
                            inputs.verify_review(raw, signature, key, expected)

    def test_unknown_phase_rejected(self):
        for phase in ("planning", "", ["review"]):
            raw, signature, key, expected = signed_review(phase, "pr-reviewer")
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                inputs.verify_review(raw, signature, key, expected)


if __name__ == "__main__":
    unittest.main()
