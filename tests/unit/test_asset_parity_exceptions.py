"""asset_parity.exceptions — 既記録の意図的非移植リストの契約。"""

import unittest

from asset_parity.exceptions import is_exempt
from asset_parity.inventory import AGENT, SKILL


class TestIsExempt(unittest.TestCase):
    def test_agy_delegate_skill_exempt_from_github(self):
        reason = is_exempt("agy-delegate", SKILL, "github")
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("非移植", reason)

    def test_agy_delegate_agent_exempt_from_github(self):
        self.assertIsNotNone(is_exempt("agy-delegate", AGENT, "github"))

    def test_issue_pipeline_skill_not_exempt_from_github(self):
        self.assertIsNone(is_exempt("issue-pipeline", SKILL, "github"))

    def test_issue_implementer_and_pr_reviewer_agents_exempt_from_github(self):
        self.assertIsNotNone(is_exempt("issue-implementer", AGENT, "github"))
        self.assertIsNotNone(is_exempt("pr-reviewer", AGENT, "github"))

    def test_non_mirror_exemptions_match_retired_assets(self):
        self.assertIsNone(is_exempt("agy-delegate", SKILL, "agents_dir"))
        self.assertIsNone(is_exempt("agy-delegate", AGENT, "codex"))
        for name, kind, tree in (("issue-pipeline", SKILL, "agents_dir"),
                                 ("issue-implementer", AGENT, "codex")):
            reason = is_exempt(name, kind, tree)
            assert reason is not None
            self.assertIn("Issue #603", reason)

    def test_unknown_asset_not_exempt(self):
        self.assertIsNone(is_exempt("not-a-real-asset", SKILL, "github"))

    def test_gh_create_issue_is_github_only_exemption(self):
        reason = is_exempt("gh-create-issue", SKILL, "github")
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("明示スコープ", reason)
        self.assertIsNone(is_exempt("gh-create-issue", SKILL, "agents_dir"))

    def test_gh_create_issue_agent_is_claude_only(self):
        self.assertIsNotNone(is_exempt("gh-create-issue", AGENT, "github"))
        self.assertIsNotNone(is_exempt("gh-create-issue", AGENT, "codex"))


if __name__ == "__main__":
    unittest.main()
