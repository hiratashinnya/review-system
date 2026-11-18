"""Issue #856: rule-to-action replay and explicit contradiction regressions.

This evaluates what the normative table prescribes for fixed cases. It is not
an LLM E2E result; a live reviewer must still follow the contract independently.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / ".ai/agents/plan-reviewer.md"

# Expected actions are independent of the Markdown table being tested.
CASES = {
    "R-856-A": ("現行AC・契約", "既存違反をfindingで報告"),
    "R-856-B": ("新たなCIの実装方式", "合格条件へ無断追加せず"),
    "R-856-C": ("不採用とした改善提案", "同じ提案を再要求しない"),
    "R-856-D": ("新しい到達経路", "実害をfindingとして報告"),
    "R-856-E": ("同じ根拠で未是正", "旧IDを参照して未解消差分を再確認"),
    "R-856-F": ("是正済みで新証拠なし", "根拠なく再指摘しない"),
    "R-856-G": ("CP/ADRが承認済みVD", "設計不整合をfindingで報告"),
    "R-856-H": ("dispatchやbranch処理", "レビュー誤指摘に算入しない"),
}

# Direct overrides of a still-present sentence must be rejected too. A
# substring-presence test alone would falsely accept these mutations.
CONTRADICTIONS = (
    r"却下済み提案[^\n]{0,90}制約は適用しない",
    r"未決[^\n]{0,110}STOP[^\n]{0,70}制約は適用しない",
    r"新しい要求[^\n]{0,150}無断[^\n]{0,70}許可する",
    r"同一根拠[^\n]{0,130}再指摘[^\n]{0,70}自由",
)


def decision_rows(text):
    rows = {}
    for line in text.splitlines():
        cols = [s.strip() for s in line.strip().strip("|").split("|")]
        if len(cols) == 3 and re.fullmatch(r"R-856-[A-H]", cols[0]):
            if cols[0] in rows:
                raise ValueError("duplicate decision example " + cols[0])
            rows[cols[0]] = (cols[1], cols[2])
    return rows


def check_contract(text):
    rows = decision_rows(text)
    if set(rows) != set(CASES):
        raise ValueError("missing or extra expected action rows")
    for key, (input_fact, action) in CASES.items():
        condition, result = rows[key]
        if input_fact not in condition or action not in result:
            raise ValueError("wrong action for " + key)
    for pattern in CONTRADICTIONS:
        if re.search(pattern, text):
            raise ValueError("conflicting normative instruction: " + pattern)


class PlanReviewDecisionExamples856Tests(unittest.TestCase):
    def test_real_scenario_actions(self):
        check_contract(CONTRACT.read_text(encoding="utf-8"))

    def test_opposite_action_mutations_go_red(self):
        text = CONTRACT.read_text(encoding="utf-8")
        rows = decision_rows(text)
        for key, (_, expected) in CASES.items():
            with self.subTest(case=key):
                self.assertIn(expected, rows[key][1])
                mutation = text.replace(expected, "無条件に合格させる")
                with self.assertRaises(ValueError):
                    check_contract(mutation)

    def test_append_only_semantic_negation_is_detected(self):
        text = CONTRACT.read_text(encoding="utf-8")
        phrase = "却下済み提案を新しい根拠なしに再要求しない。"
        self.assertIn(phrase, text)
        mutated = text.replace(
            phrase, "却下済み提案を新しい根拠なしに再要求しない、という制約は適用しない。")
        with self.assertRaisesRegex(ValueError, "conflicting normative"):
            check_contract(mutated)


if __name__ == "__main__":
    unittest.main()
