"""Issue #856 source-linked regression guards; no fabricated reviewer runtime.

The fixtures are observations, not a claim to have run an LLM or to have
recovered original 1a/1b PlanReview handoffs.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "audit/2026-11-17-plan-review-856/cases.json"
CONTRACT = ROOT / ".ai/agents/plan-reviewer.md"
AUDIT = ROOT / "audit/2026-11-17-plan-review-856/README.md"


def load_cases():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if data["schema"] != "plan-review-evidence-856/v1":
        raise ValueError("unsupported evidence fixture schema")
    return data["cases"]


def missing_guards(contract, case):
    return [token for token in case["contract_anchor"] if token not in contract]


class PlanReviewRealEvidence856Tests(unittest.TestCase):
    def test_provenance_and_case_coverage(self):
        cases = load_cases()
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        self.assertGreaterEqual(len(cases), 8)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["source"].startswith(
                    "https://github.com/hiratashinnya/review-system/"))
                self.assertTrue(case["observed"])
                self.assertTrue(case["classification"])
                self.assertTrue(case["contract_anchor"])
        self.assertTrue(any(c["phase"] == "1a" for c in cases))
        self.assertTrue(any(c["kind"] == "design-review-karte" for c in cases))
        self.assertTrue(any(c["kind"] == "pr-review-recheck" for c in cases))

    def test_each_real_case_is_guarded_by_review_contract(self):
        contract = CONTRACT.read_text(encoding="utf-8")
        for case in load_cases():
            with self.subTest(case=case["id"]):
                self.assertEqual(missing_guards(contract, case), [])

    def test_every_case_has_a_detectable_rule_removal(self):
        contract = CONTRACT.read_text(encoding="utf-8")
        for case in load_cases():
            for guard in case["contract_anchor"]:
                with self.subTest(case=case["id"], deleted=guard):
                    self.assertIn(guard, contract)
                    changed = contract.replace(guard, "")
                    self.assertIn(guard, missing_guards(changed, case))

    def test_round_recheck_keeps_original_finding_identity(self):
        cases = load_cases()
        for case in cases:
            with self.subTest(case=case["id"]):
                rounds = case["rounds"]
                self.assertEqual(rounds, sorted(set(rounds)))
                if case["resolved_round"] is not None:
                    self.assertIn(case["resolved_round"], rounds)
                    self.assertGreaterEqual(len(rounds), 2)
                    self.assertEqual(len(case["finding_ids"]), 1)
        self.assertEqual(next(c for c in cases if c["id"] == "809-F01-design")
                         ["rounds"], [1, 2])
        self.assertEqual(next(c for c in cases if c["id"] == "809-F07-design")
                         ["resolved_round"], 3)

    def test_non_planreview_cases_are_not_claimed_as_1a_1b(self):
        cases = load_cases()
        for case in cases:
            if case["kind"] in ("design-review-karte", "pr-review-recheck",
                                "pr-review-finding", "pr-review-owner-decision"):
                self.assertNotIn(case["phase"], ("1a", "1b"))
        audit = AUDIT.read_text(encoding="utf-8")
        self.assertIn("F-809-01", audit)
        self.assertIn("PR #731", audit)
        self.assertIn("原本未取得", audit)


if __name__ == "__main__":
    unittest.main()
