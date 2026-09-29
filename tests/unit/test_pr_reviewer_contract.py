"""PR reviewer の差分取得契約を検証する。"""

import re
import unittest
from pathlib import Path


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


    def test_all_contracts_require_self_report_when_full_diff_is_unconfirmed(self):
        repository_root = Path(__file__).resolve().parents[2]
        contract_paths = (
            ".ai/agents/pr-reviewer.md",
            ".claude/agents/pr-reviewer.md",
            ".codex/agents/pr-reviewer.toml",
        )
        for relative_path in contract_paths:
            text = (repository_root / relative_path).read_text(encoding="utf-8")
            with self.subTest(path=relative_path):
                self.assertIn("未確認の差分", text)
                self.assertIn("`harm: real` / `severity: blocker` / `scope: in`", text)
                self.assertIn("STOP", text)


if __name__ == "__main__":
    unittest.main()
