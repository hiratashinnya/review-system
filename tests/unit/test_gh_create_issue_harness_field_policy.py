"""GitHub Issue 作成時の Project Harness field 規律を検査する。"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SKILL = (ROOT / ".ai/skills/gh-create-issue/SKILL.md").read_text(
    encoding="utf-8"
)
TROUBLESHOOTING = (ROOT / ".ai/troubleshooting/gh-create-issue.md").read_text(
    encoding="utf-8"
)
AGENT = (ROOT / ".claude/agents/gh-create-issue.md").read_text(encoding="utf-8")


class HarnessFieldPolicyTests(unittest.TestCase):
    def test_only_explicit_issue_body_harness_names_are_set(self):
        project_rules = SKILL.split("### Project field rules", 1)[1].split(
            "### Project へ書き込めない実行環境", 1
        )[0]
        self.assertIn("Issue 本文に対象 harness が明記されている場合に限り", project_rules)
        self.assertIn("本文に記載がなければ設定せず、確認質問もしない", project_rules)
        self.assertNotIn("`area:harness` を付けた場合は", project_rules)

    def test_harness_omission_does_not_trigger_owner_confirmation(self):
        self.assertIn("未記載を理由に停止・質問しない", SKILL)
        self.assertIn("その未記載を確認事項にしない", AGENT)
        self.assertIn("未指定・変更対象外」として質問しない", TROUBLESHOOTING)


if __name__ == "__main__":
    unittest.main()
