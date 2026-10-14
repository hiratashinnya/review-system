"""asset_parity.copilot_paths — Copilot (`.github/`) パスの単一定義の契約。

copilot_paths.py が「Copilot パスの単一定義」を名乗れるのは、他モジュールが `.github` を
直書きしていない間だけである。名乗りと実態の食い違い（パス変更で直す箇所が散らばる）を
ここで機械的に固定する。
"""

import ast
import unittest
from pathlib import Path

import asset_parity
from asset_parity.copilot_paths import (
    copilot_agent_path,
    copilot_instructions_path,
    copilot_mirror_roots,
    copilot_prompt_path,
    copilot_skill_path,
    inline_slot_path,
)
from asset_parity.inventory import AGENT, SKILL

ROOT = Path("/repo")
PACKAGE_DIR = Path(asset_parity.__file__).resolve().parent
DEFINITION_MODULE = "copilot_paths.py"


def _github_dir_literals(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value == ".github"
    ]


class TestCopilotPaths(unittest.TestCase):
    def test_file_paths(self):
        self.assertEqual(copilot_skill_path("x", ROOT), ROOT / ".github/skills/x/SKILL.md")
        self.assertEqual(copilot_prompt_path("x", ROOT), ROOT / ".github/prompts/x.prompt.md")
        self.assertEqual(copilot_agent_path("x", ROOT), ROOT / ".github/agents/x.agent.md")
        self.assertEqual(copilot_instructions_path(ROOT), ROOT / ".github/copilot-instructions.md")

    def test_inline_slot_lies_under_the_instructions_file(self):
        slot = inline_slot_path("x", ROOT)
        self.assertEqual(slot.parent, copilot_instructions_path(ROOT))

    def test_mirror_roots_contain_the_expected_files(self):
        agent_roots = copilot_mirror_roots(AGENT, ROOT)
        self.assertIn(copilot_agent_path("x", ROOT).parent, agent_roots)
        skill_roots = copilot_mirror_roots(SKILL, ROOT)
        self.assertIn(copilot_skill_path("x", ROOT).parent.parent, skill_roots)
        self.assertIn(copilot_prompt_path("x", ROOT).parent, skill_roots)


class TestSingleDefinition(unittest.TestCase):
    def test_only_copilot_paths_module_spells_the_github_directory(self):
        stray = {
            module.name: lines
            for module in sorted(PACKAGE_DIR.glob("*.py"))
            if module.name != DEFINITION_MODULE and (lines := _github_dir_literals(module))
        }
        self.assertEqual(
            stray, {},
            "asset_parity modules other than copilot_paths.py spell the '.github' directory "
            "themselves; move the path into copilot_paths.py so it stays the single definition",
        )

    def test_definition_module_does_spell_it(self):
        self.assertTrue(_github_dir_literals(PACKAGE_DIR / DEFINITION_MODULE))


if __name__ == "__main__":
    unittest.main()
