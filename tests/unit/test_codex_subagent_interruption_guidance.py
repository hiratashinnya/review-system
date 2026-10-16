"""Codex サブエージェント中断対策指示の回帰テスト。"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_LINES = (
    "サブエージェントの作業が完了し、結果を確認できるまで、このターンを終了・中断しないでください。",
    "サブエージェントの結果を受け取ってから最終回答してください。",
    "サブエージェントが作業に時間がかかっている場合は、進捗確認のメッセージを送り、状況を確認してください。",
)
CODEX_AGENT_FILES = (
    ROOT / ".codex/agents/authoring-fanout.toml",
)
RETIRED_CODEX_AGENT_FILES = (
    ROOT / "archive/issue-603-codex-main-context-assets/.codex/agents/issue-implementer.toml",
    ROOT / "archive/issue-603-codex-main-context-assets/.codex/agents/issue-fixer.toml",
    ROOT / "archive/issue-603-codex-main-context-assets/.codex/agents/pr-reviewer.toml",
)


class TestCodexSubagentInterruptionGuidance(unittest.TestCase):
    def test_required_guidance_exists_in_codex_agents(self):
        for path in CODEX_AGENT_FILES:
            self.assertTrue(path.exists(), msg=f"{path} が存在しません")
            text = path.read_text(encoding="utf-8")
            for line in REQUIRED_LINES:
                with self.subTest(path=str(path), line=line):
                    self.assertIn(line, text)

    def test_retired_agents_remain_archived_and_registry_records_retirement(self):
        for path in RETIRED_CODEX_AGENT_FILES:
            with self.subTest(path=str(path)):
                self.assertTrue(path.exists(), msg=f"{path} が archive にありません")
        registry = (ROOT / ".claude/tailoring-registry.md").read_text(encoding="utf-8")
        self.assertIn(
            "Issue #603 で `.agents/skills/issue-pipeline/SKILL.md` と "
            "`.codex/agents/{issue-implementer,issue-fixer,pr-reviewer}.toml`",
            registry,
        )
        self.assertIn("退役する", registry)


if __name__ == "__main__":
    unittest.main()
