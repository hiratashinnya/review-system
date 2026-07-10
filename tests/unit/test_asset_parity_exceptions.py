"""asset_parity.exceptions — 既記録の意図的非移植リストの契約。"""

import unittest

from asset_parity.exceptions import is_exempt
from asset_parity.inventory import AGENT, SKILL


class TestIsExempt(unittest.TestCase):
    def test_agy_delegate_skill_exempt_from_github(self):
        reason = is_exempt("agy-delegate", SKILL, "github")
        self.assertIsNotNone(reason)
        self.assertIn("非移植", reason)

    def test_agy_delegate_agent_exempt_from_github(self):
        self.assertIsNotNone(is_exempt("agy-delegate", AGENT, "github"))

    def test_issue_pipeline_skill_exempt_from_github(self):
        self.assertIsNotNone(is_exempt("issue-pipeline", SKILL, "github"))

    def test_issue_implementer_and_pr_reviewer_agents_exempt_from_github(self):
        self.assertIsNotNone(is_exempt("issue-implementer", AGENT, "github"))
        self.assertIsNotNone(is_exempt("pr-reviewer", AGENT, "github"))

    def test_not_exempt_from_codex_or_agents_dir(self):
        # 2026-07 時点で Codex には移植済み（issue #155 是正コミット）— exempt 登録は github のみ。
        self.assertIsNone(is_exempt("agy-delegate", SKILL, "agents_dir"))
        self.assertIsNone(is_exempt("agy-delegate", AGENT, "codex"))
        self.assertIsNone(is_exempt("issue-pipeline", SKILL, "agents_dir"))
        self.assertIsNone(is_exempt("issue-implementer", AGENT, "codex"))

    def test_unknown_asset_not_exempt(self):
        self.assertIsNone(is_exempt("not-a-real-asset", SKILL, "github"))


if __name__ == "__main__":
    unittest.main()
