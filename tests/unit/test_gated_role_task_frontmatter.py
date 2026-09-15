"""Issue #517 第一層の回帰テスト: gated ロールの frontmatter `tools:` に `Task` が無いこと。

`issue-implementer`/`issue-fixer` は Task を保有していたため、ゲート対象外のサブエージェント
（`general-purpose` 等）を spawn して `.claude/hooks/agent-command-gate.sh` の allowlist を
迂回できた（PR #516 の実装中に実測・詳細は Issue #517）。frontmatter から `Task` を外すことが
構造的 fail-close の第一層であり、`Task` の `PreToolUse`（`issue_start/gate.py` の
`GATED_ROLES`/`_caller_agent_type`）が復元時の第二層になる。本テストは第一層が今後の編集で
無言のうちに巻き戻らないことを機械的に固定する。

標準ライブラリのみで frontmatter の `tools:` 行を素朴にパースする（本リポジトリのフロントマターは
自前パーサ方針＝Q5/Q5a と同じ考え方——YAML ライブラリへ依存しない）。
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

# `pr-reviewer` はそもそも `Task` を保有していない（Issue #517 の out of scope）ため対象外。
GATED_ROLE_AGENT_FILES = {
    "issue-implementer": ROOT / ".claude/agents/issue-implementer.md",
    "issue-fixer": ROOT / ".claude/agents/issue-fixer.md",
}


def _tools_line(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "---", f"{path}: frontmatter must start with '---'"
    end = lines.index("---", 1)
    frontmatter = lines[1:end]
    tools_lines = [line for line in frontmatter if line.startswith("tools:")]
    assert len(tools_lines) == 1, f"{path}: expected exactly one 'tools:' line"
    return tools_lines[0]


class GatedRoleTaskFrontmatterTests(unittest.TestCase):
    def test_gated_role_frontmatter_does_not_list_task(self):
        for role, path in GATED_ROLE_AGENT_FILES.items():
            with self.subTest(role=role):
                tools_line = _tools_line(path)
                declared = [
                    tool.strip()
                    for tool in tools_line[len("tools:"):].split(",")
                    if tool.strip()
                ]
                self.assertNotIn(
                    "Task", declared,
                    f"{path} must not grant Task (Issue #517 layer 1 — a gated role with "
                    "Task can spawn ungated subagents and bypass agent-command-gate.sh)",
                )

    def test_gated_role_frontmatter_still_lists_the_expected_non_task_tools(self):
        # allow-form: 除去が Task だけに限定されていること（他ツールを巻き込んで壊していない）。
        expected_present = {
            "Read", "Grep", "Glob", "Write", "Edit", "Bash",
            "mcp__plugin_context-mode_context-mode__ctx_batch_execute",
            "mcp__plugin_context-mode_context-mode__ctx_execute",
        }
        for role, path in GATED_ROLE_AGENT_FILES.items():
            with self.subTest(role=role):
                tools_line = _tools_line(path)
                declared = {
                    tool.strip()
                    for tool in tools_line[len("tools:"):].split(",")
                    if tool.strip()
                }
                self.assertEqual(declared, expected_present)


if __name__ == "__main__":
    unittest.main()
