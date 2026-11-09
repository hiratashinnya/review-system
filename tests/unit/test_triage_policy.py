"""Issue #781: decision-table positive and fail-closed negative examples."""

import copy
import json
from pathlib import Path
import unittest

from triage_policy import evaluate, load_policy, policy_digest, suggest
from triage_policy.contract import BOOLEANS, validate_policy


def evidence(**changes):
    result = dict.fromkeys(BOOLEANS, False)
    result.update(finding_id="F-781-01", policy_ref="review-finding-disposition@1.0",
                  phase="review", harm="real", severity="minor", scope="in",
                  reviewer_verified=True, evidence_complete=True,
                  ac_relation_verified=True)
    result.update(changes)
    return result


def approval(policy, **changes):
    result = dict(verified_by_trusted_cli=True, owner="actual-owner",
                  feedback_ref="FBK-20261110-approved-triage", policy_ref="review-finding-disposition@1.0",
                  policy_digest=policy_digest(policy),
                  allowed_dispositions=["fix-here", "deferred", "advisory"],
                  allowed_phases=["review", "remediation_review"])
    result.update(changes)
    return result


class TestTriagePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()

    def test_default_is_disabled_and_matches_schema(self):
        self.assertEqual(validate_policy(self.policy), [])
        self.assertEqual(self.policy["status"], "draft")
        self.assertFalse(self.policy["auto_apply_enabled"])
        self.assertTrue(all(value is False for value in self.policy["feature_flags"].values()))

    def test_machine_schema_matches_runtime_rule_order(self):
        schema_path = (Path(__file__).resolve().parents[2] / ".ai" / "schema"
                       / "triage-policy-v1.json")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        rules = schema["properties"]["rules"]
        self.assertEqual([entry["properties"]["outcome"]["const"]
                          for entry in rules["prefixItems"]],
                         [entry["outcome"] for entry in self.policy["rules"]])
        self.assertIs(rules["items"], False)
        for key in ("all_true", "all_false", "any_true"):
            self.assertEqual(schema["$defs"]["rule"]["properties"][key]["items"]["enum"],
                             list(BOOLEANS))
        self.assertEqual(schema["$defs"]["finding_evidence"]["properties"]
                         ["finding_id"]["minLength"], 1)

    def test_scope_out_does_not_waive_required_fix(self):
        self.assertEqual(suggest(self.policy, evidence(scope="out", ac_violation=True))
                         ["candidate"], "fix-here")

    def test_mandatory_violations_have_priority(self):
        for key in ("ac_violation", "design_violation", "contract_violation", "regression"):
            with self.subTest(key=key):
                finding = evidence(**{key: True}, preexisting=True)
                self.assertEqual(suggest(self.policy, finding)["candidate"], "fix-here")

    def test_existing_minor_is_deferred_candidate_only(self):
        finding = evidence(preexisting=True)
        self.assertEqual(suggest(self.policy, finding)["candidate"], "deferred")
        result = evaluate(self.policy, finding, approval(self.policy))
        self.assertFalse(result["auto_applicable"])
        self.assertEqual(result["disposition"], "owner-review")

    def test_optional_no_harm_is_advisory_candidate_only(self):
        finding = evidence(harm="none", optional_improvement=True)
        self.assertEqual(suggest(self.policy, finding)["candidate"], "advisory")
        self.assertEqual(evaluate(self.policy, finding)["disposition"], "owner-review")

    def test_missing_evidence_fails_closed(self):
        for key in ("regression", "ac_relation_verified", "reviewer_verified", "handoff_verified"):
            finding = evidence(ac_violation=True)
            del finding[key]
            with self.subTest(key=key):
                self.assertEqual(suggest(self.policy, finding)["candidate"], "owner-review")

    def test_conflict_risk_owner_authority(self):
        for key in ("reviewer_conflict", "scope_override_requested", "high_risk",
                    "spec_decision_required", "scope_expansion_required"):
            with self.subTest(key=key):
                self.assertEqual(suggest(self.policy, evidence(ac_violation=True, **{key: True}))
                                 ["candidate"], "owner-review")

    def test_no_harm_with_required_fix_is_conflict(self):
        self.assertEqual(suggest(self.policy, evidence(harm="none", regression=True))
                         ["reason_codes"], ["harm-contradicts-mandatory"])

    def test_unsafe_deferred_or_advisory_rejected(self):
        for change in (dict(preexisting=True, worsened=True),
                       dict(preexisting=True, severity="major"),
                       dict(harm="real", optional_improvement=True),
                       dict(harm="none", optional_improvement=False)):
            with self.subTest(change=change):
                self.assertEqual(suggest(self.policy, evidence(**change))["candidate"],
                                 "owner-review")

    def test_no_policy_version_or_bad_rule_fails_closed(self):
        for mutation in (dict(policy_version="2.0"), dict(policy_id="unknown"),
                         dict(enabled_phases=["planning"]),
                         dict(feature_flags={"fix-here": True}),
                         dict(rules=[{"outcome": "advisory"}])):
            copy_policy = copy.deepcopy(self.policy)
            copy_policy.update(mutation)
            with self.subTest(mutation=mutation):
                self.assertEqual(suggest(copy_policy, evidence(ac_violation=True))
                                 ["candidate"], "owner-review")

    def test_policy_ref_mismatch_and_unknown_phase(self):
        for finding in (evidence(policy_ref="review-finding-disposition@2.0"),
                        evidence(phase="planning")):
            self.assertEqual(suggest(self.policy, finding)["candidate"], "owner-review")

    def test_tampered_or_missing_approval_cannot_activate(self):
        policy = copy.deepcopy(self.policy)
        policy.update(status="approved", auto_apply_enabled=True)
        policy["feature_flags"]["fix-here"] = True
        finding = evidence(ac_violation=True)
        cases = (None, approval(policy, verified_by_trusted_cli=False),
                 approval(policy, policy_digest="forged"),
                 approval(policy, feedback_ref=""),
                 approval(policy, allowed_dispositions=["advisory"]),
                 approval(policy, allowed_phases=["planning"]))
        for proof in cases:
            with self.subTest(proof=proof):
                self.assertFalse(evaluate(policy, finding, proof,
                                          verify_owner=lambda p, digest: True)["auto_applicable"])

    def test_explicit_approval_enables_only_selected_result(self):
        policy = copy.deepcopy(self.policy)
        policy.update(status="approved", auto_apply_enabled=True)
        policy["feature_flags"]["fix-here"] = True
        self.assertFalse(evaluate(policy, evidence(ac_violation=True), approval(policy))["auto_applicable"])
        result = evaluate(policy, evidence(ac_violation=True), approval(policy),
                          verify_owner=lambda proof, digest: proof["policy_digest"] == digest)
        self.assertEqual(result["disposition"], "fix-here")
        self.assertTrue(result["auto_applicable"])
        policy["auto_apply_enabled"] = False
        self.assertFalse(evaluate(policy, evidence(ac_violation=True), approval(policy),
                                  verify_owner=lambda proof, digest: proof["policy_digest"] == digest)["auto_applicable"])

    def test_trusted_verifier_fail_closed(self):
        policy = copy.deepcopy(self.policy)
        policy.update(status="approved", auto_apply_enabled=True)
        policy["feature_flags"]["fix-here"] = True
        finding = evidence(ac_violation=True)
        for fn in (None, lambda p, d: False, lambda p, d: "truthy",
                   lambda p, d: 1 / 0):
            with self.subTest(verifier=fn):
                self.assertFalse(evaluate(policy, finding, approval(policy),
                                          verify_owner=fn)["auto_applicable"])

    def test_deferred_and_advisory_require_verified_destinations(self):
        policy = copy.deepcopy(self.policy)
        policy.update(status="approved", auto_apply_enabled=True)
        policy["feature_flags"].update({"deferred": True, "advisory": True})
        for candidate, finding, confirmed in (
            ("deferred", evidence(preexisting=True), evidence(preexisting=True, handoff_verified=True)),
            ("advisory", evidence(harm="none", optional_improvement=True),
             evidence(harm="none", optional_improvement=True, advisory_verified=True)),
        ):
            with self.subTest(candidate=candidate):
                self.assertFalse(evaluate(policy, finding, approval(policy),
                                          verify_owner=lambda proof, digest: True)["auto_applicable"])
                self.assertEqual(evaluate(policy, confirmed, approval(policy),
                                          verify_owner=lambda proof, digest: True)["disposition"], candidate)


if __name__ == "__main__":
    unittest.main()
