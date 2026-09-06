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
    ROOT / ".codex/agents/issue-implementer.toml",
    ROOT / ".codex/agents/pr-reviewer.toml",
)


class TestCodexSubagentInterruptionGuidance(unittest.TestCase):
    def test_required_guidance_exists_in_codex_agents(self):
        for path in CODEX_AGENT_FILES:
            self.assertTrue(path.exists(), msg=f"{path} が存在しません")
            text = path.read_text(encoding="utf-8")
            for line in REQUIRED_LINES:
                with self.subTest(path=str(path), line=line):
                    self.assertIn(line, text)

    def test_tailoring_registry_records_codex_only_non_mirror(self):
        registry = (ROOT / ".claude/tailoring-registry.md").read_text(encoding="utf-8")
        self.assertIn("Codex 側のサブエージェント中断対策指示", registry)
        self.assertIn("他 PF へはミラーしない", registry)


if __name__ == "__main__":
    unittest.main()
