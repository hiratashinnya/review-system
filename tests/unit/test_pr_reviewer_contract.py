"""PR reviewer の差分取得契約を検証する。"""

import re
import unittest
from pathlib import Path


DIFF_FINDING_RULE = re.compile(
    r"差分全文を取得・確認できなかった場合.*?`harm: real` / `severity: blocker` / `scope: in` の finding として自己申告し、判定を STOP にする。"
    r"未確認範囲が PR 差分全体なら locus は `PR#<N>::diff` とし、一部ファイルだけ未確認ならそのファイルのパスを locus とする。"
    r"保存ファイルは Read で 1 行目から末尾まで重複や欠番なく連続する範囲で読み、利用可能なマニフェストの `lines` と照合し、終端改行を表示用の空行として別番号にしている場合はその空行を除いた最終データ行番号が `lines` と一致することを確認する。"
    r"Read では SHA-256 を計算できないため、SHA-256 は判定条件にしない。"
)


def required_diff_finding_rules(text):
    return [
        match.group(0)
        for line in text.splitlines()
        if "差分全文を取得・確認できなかった場合" in line
        for match in DIFF_FINDING_RULE.finditer(line)
    ]


class PrReviewerContractTests(unittest.TestCase):
    def test_all_pr_diff_commands_require_rtk_prefix(self):
        repository_root = Path(__file__).resolve().parents[2]
        contract_paths = (
            ".ai/agents/pr-reviewer.md",
            ".claude/agents/pr-reviewer.md",
            ".codex/agents/pr-reviewer.toml",
        )
        for relative_path in contract_paths:
            contract_path = repository_root / relative_path
            lines = contract_path.read_text(encoding="utf-8").splitlines()
            diff_lines = [line for line in lines if "gh pr diff" in line]
            with self.subTest(path=relative_path):
                self.assertTrue(diff_lines)
                for line in diff_lines:
                    self.assertIn("rtk gh pr diff", line)
                    self.assertNotRegex(line, re.compile(r"(?<!rtk )gh pr diff"))


    def test_all_contracts_bind_unconfirmed_diff_to_finding_locus_and_read_check(self):
        repository_root = Path(__file__).resolve().parents[2]
        contract_paths = (
            ".ai/agents/pr-reviewer.md",
            ".claude/agents/pr-reviewer.md",
            ".codex/agents/pr-reviewer.toml",
        )
        matched_rules = []
        for relative_path in contract_paths:
            text = (repository_root / relative_path).read_text(encoding="utf-8")
            with self.subTest(path=relative_path):
                rules = required_diff_finding_rules(text)
                self.assertEqual(len(rules), 1)
                matched_rules.extend(rules)
        self.assertEqual(len(matched_rules), len(contract_paths))
        self.assertEqual(len(set(matched_rules)), 1)

    def test_contract_assertion_fails_for_negated_stop_rule(self):
        repository_root = Path(__file__).resolve().parents[2]
        contract_path = repository_root / ".ai/agents/pr-reviewer.md"
        text = contract_path.read_text(encoding="utf-8")
        rule = required_diff_finding_rules(text)[0]
        negated_rule = rule.replace("判定を STOP にする", "判定を STOP にしない", 1)
        self.assertNotEqual(rule, negated_rule)
        negated_text = text.replace(rule, negated_rule, 1)
        with self.assertRaises(AssertionError):
            self.assertEqual(len(required_diff_finding_rules(negated_text)), 1)


if __name__ == "__main__":
    unittest.main()
