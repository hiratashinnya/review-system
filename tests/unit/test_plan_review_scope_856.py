"""Issue #856: PlanReview phase and owner-boundary contract regression.

These are normative-contract guards, not a simulated LLM or a triage classifier.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
REVIEWER = ROOT / ".ai/agents/plan-reviewer.md"
COMMON = ROOT / ".ai/agents/creation-stage-contract.md"

# Each scenario names an expected decision boundary; these fragments are contractual,
# rather than a fabricated machine classification of reviewer findings.
CASES = {
    "1a_validates_vd_not_implementation": (
        "## 1a：検証設計", "何を満たせば合格か", "実現手段を確定・強制せず",
    ),
    "1a_checks_ac_and_real_harm": (
        "各ACを①機械判定可能性", "当該ACの文言", "重大な実害",
    ),
    "1b_compares_cp_adr_vd": (
        "## 1b：解決設計", "どう満たすか", "合格済みVD",
    ),
    "1b_reuses_prior_decisions_but_catches_new_defects": (
        "合格済みの個別判定", "新たに判明した不整合", "前回判定との差分",
    ),
    "new_requirement_does_not_become_an_ac": (
        "新しい要求・AC文言変更・Scope拡張", "追加しない", "STOPする",
    ),
    "missing_evidence_does_not_suppress_finding": (
        "裏付けが取れない点は断定せず", "findingを省略・自動棄却しない",
        "`根拠なし`", "review-finding-basis.md",
    ),
    "repeat_finding_requires_prior_evidence": (
        "前回finding", "依然残る差分または新証拠", "再掲を省略せず",
    ),
    "rejected_request_not_reintroduced": (
        "却下済み提案", "新しい根拠なしに再要求しない",
    ),
    "dispatch_failure_not_review_error": (
        "dispatch/branch/recovery障害", "PlanReview観点の誤りと混同しない",
    ),
    "reviewer_does_not_auto_triage": (
        "finding-triagerの独立評価", "兼務しない", "owner判断は行わない",
    ),
}


def assert_scenario(contract: str, clauses: tuple[str, ...]) -> None:
    for clause in clauses:
        if clause not in contract:
            raise AssertionError(f"missing PlanReview contract clause: {clause}")


class PlanReviewerIssue856Tests(unittest.TestCase):
    def test_scenarios_are_independently_guarded(self):
        contract = REVIEWER.read_text(encoding="utf-8")
        for name, clauses in CASES.items():
            with self.subTest(scenario=name):
                assert_scenario(contract, clauses)

    def test_removing_each_scenario_rule_fails(self):
        contract = REVIEWER.read_text(encoding="utf-8")
        for name, clauses in CASES.items():
            with self.subTest(scenario=name):
                changed = contract.replace(clauses[0], "", 1)
                self.assertNotEqual(changed, contract)
                with self.assertRaises(AssertionError):
                    assert_scenario(changed, clauses)

    def test_shared_contract_references_single_normative_source(self):
        common = COMMON.read_text(encoding="utf-8")
        self.assertIn("[plan-reviewer共通契約](plan-reviewer.md)", common)
        self.assertIn("軽量Issueでも1a/1b/2aと各レビューは省略せず", common)
        self.assertIn("owner判断を代行しない", common)

    def test_reviewer_retains_independent_review_and_harm_source(self):
        text = REVIEWER.read_text(encoding="utf-8")
        self.assertIn(".ai/skills/review-harm/SKILL.md", text)
        self.assertIn("全文を必ず読み", text)
        self.assertIn("別dispatch", text)
        self.assertIn("PlanReviewをcommitted envelopeとして書かず", text)
        self.assertIn("主文脈がkarteへ取り込む", text)


if __name__ == "__main__":
    unittest.main()
