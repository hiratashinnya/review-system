"""silent-failure-diagnosis の配置契約（Issue #605）を固定する。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NAME = "silent-failure-diagnosis"
COMMON = f".ai/skills/{NAME}/SKILL.md"
RATIONALE = f".ai/rationale/{NAME}.md"
CLAUDE_WRAPPER = f".claude/skills/{NAME}/SKILL.md"
CODEX_WRAPPER = f".agents/skills/{NAME}/SKILL.md"
COMMON_HREF = f"../../../{COMMON}"


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _frontmatter(body: str) -> str:
    match = re.match(r"\A---\n(.*?)\n---\n", body, re.DOTALL)
    if match is None:
        raise AssertionError("wrapper に frontmatter が無い")
    return match.group(1)


class WrapperConnectionTests(unittest.TestCase):
    def test_wrappers_point_to_common_body_without_copying_it(self):
        for rel in (CLAUDE_WRAPPER, CODEX_WRAPPER):
            with self.subTest(wrapper=rel):
                body = _read(rel)
                self.assertIn(f"name: {NAME}", _frontmatter(body))
                self.assertIn(COMMON_HREF, body)
                self.assertNotIn("## D0.", body)

    def test_only_claude_wrapper_declares_shared_reference(self):
        self.assertIn("user-invocable: false", _frontmatter(_read(CLAUDE_WRAPPER)))
        self.assertNotIn("user-invocable", _frontmatter(_read(CODEX_WRAPPER)))

    def test_copilot_is_intentionally_not_deployed(self):
        for rel in (f".github/skills/{NAME}", f".github/prompts/{NAME}.prompt.md"):
            self.assertFalse((REPO_ROOT / rel).exists(), rel)
        self.assertNotIn(NAME, _read(".github/copilot-instructions.md"))


class CommonBodyContractTests(unittest.TestCase):
    def test_common_body_is_pf_neutral_markdown(self):
        body = _read(COMMON)
        self.assertIsNone(re.match(r"\A---\n", body))
        for token in ("user-invocable", "claude-code-guide", "effort:"):
            self.assertNotIn(token, body)

    def test_general_rules_and_division_are_present(self):
        body = _read(COMMON)
        for number in range(9):
            self.assertIn(f"## D{number}.", body)
        self.assertIn("## 一般則とツール固有事象の分担", body)

    def test_agy_exit_zero_denial_is_an_example_owned_by_the_tool_asset(self):
        body = _read(COMMON)
        example = body[body.index("> **事例（agy") :]
        self.assertIn("終了コード 0・`status: SUCCESS`", example)
        self.assertIn("正本は `agy-delegate`", example)

    def test_rationale_is_reachable_and_non_normative(self):
        self.assertIn(f"../../rationale/{NAME}.md", _read(COMMON))
        rationale = _read(RATIONALE)
        self.assertIn("これは規範ではない", rationale)
        self.assertIn(COMMON, rationale)


if __name__ == "__main__":
    unittest.main()
