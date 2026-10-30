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
    def test_harness_is_recorded_in_issue_body_not_project_field(self):
        body_rules = SKILL.split("## 4. Issue を単一成果に整形する", 1)[1].split(
            "## 5. labels と Project fields を決める", 1
        )[0]
        self.assertIn("`## 対象 harness`", body_rules)
        self.assertIn("本文を正本", body_rules)
        self.assertIn("field 設定不可を理由に作成・完了を停止しない", body_rules)

        project_rules = SKILL.split("### Project field rules", 1)[1].split(
            "### Project へ書き込めない実行環境", 1
        )[0]
        self.assertIn("Project field としての設定・確認をしない", project_rules)
        self.assertIn("`Harness` field は照合対象にしない", SKILL)

    def test_harness_field_unavailability_is_not_a_stop_condition(self):
        self.assertIn("その field を設定できないことを理由に停止", TROUBLESHOOTING)
        self.assertIn("field 設定不可を理由に停止・質問しない", AGENT)


if __name__ == "__main__":
    unittest.main()
