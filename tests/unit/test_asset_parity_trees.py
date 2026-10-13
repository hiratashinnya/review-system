"""asset_parity.trees — ツリー別命名規則・skill/prompt 振り分けの契約。"""

import tempfile
import unittest
from pathlib import Path

from asset_parity.inventory import AGENT, MODE_ORCHESTRATOR, MODE_PRINCIPLE, MODE_SKILL, SKILL, Asset
from asset_parity.trees import AGENTS_DIR, CODEX, GITHUB, applicable_trees, expected_paths


ROOT = Path("/repo")


def _skill(name, mode=MODE_SKILL):
    return Asset(name=name, kind=SKILL, mode=mode, parity_seed_path=ROOT / ".claude/skills" / name / "SKILL.md")


def _agent(name):
    return Asset(name=name, kind=AGENT, mode=None, parity_seed_path=ROOT / ".claude/agents" / f"{name}.md")


def _marker_line(skill_name):
    return f"<!-- principles-source: .ai/skills/{skill_name}/SKILL.md; sha256: 0 -->\n"


def _write_instructions(root, text):
    instructions = root / ".github" / "copilot-instructions.md"
    instructions.parent.mkdir(parents=True)
    instructions.write_text(text, encoding="utf-8")


class TestApplicableTrees(unittest.TestCase):
    def test_skill_applies_to_github_and_agents_dir_only(self):
        self.assertEqual(set(applicable_trees(SKILL)), {GITHUB, AGENTS_DIR})

    def test_agent_applies_to_github_and_codex_only(self):
        self.assertEqual(set(applicable_trees(AGENT)), {GITHUB, CODEX})


class TestExpectedPaths(unittest.TestCase):
    def test_plain_skill_github_path(self):
        paths = expected_paths(_skill("align"), GITHUB, ROOT)
        self.assertEqual(paths, [ROOT / ".github/skills/align/SKILL.md"])

    def test_plain_skill_agents_dir_path(self):
        paths = expected_paths(_skill("align"), AGENTS_DIR, ROOT)
        self.assertEqual(paths, [ROOT / ".agents/skills/align/SKILL.md"])

    def test_orchestrator_skill_github_uses_prompt_path(self):
        paths = expected_paths(_skill("spec-pipeline", MODE_ORCHESTRATOR), GITHUB, ROOT)
        self.assertEqual(paths, [ROOT / ".github/prompts/spec-pipeline.prompt.md"])

    def test_orchestrator_skill_agents_dir_uses_plain_skill_path(self):
        paths = expected_paths(_skill("spec-pipeline", MODE_ORCHESTRATOR), AGENTS_DIR, ROOT)
        self.assertEqual(paths, [ROOT / ".agents/skills/spec-pipeline/SKILL.md"])

    def test_inlined_principle_skill_github_expects_no_discrete_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_instructions(root, _marker_line("some-principle"))
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self.assertEqual(expected_paths(asset, GITHUB, root), [])

    def test_uninlined_principle_skill_github_expects_plain_skill_path(self):
        # instructions exist but name only another skill: this one is not inlined
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_instructions(root, _marker_line("some-other-principle"))
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self.assertEqual(
                expected_paths(asset, GITHUB, root), [root / ".github/skills/some-principle/SKILL.md"]
            )

    def test_principle_skill_without_instructions_file_expects_plain_skill_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self.assertEqual(
                expected_paths(asset, GITHUB, root), [root / ".github/skills/some-principle/SKILL.md"]
            )

    def test_principle_skill_agents_dir_uses_plain_skill_path(self):
        paths = expected_paths(_skill("spec-principles", MODE_PRINCIPLE), AGENTS_DIR, ROOT)
        self.assertEqual(paths, [ROOT / ".agents/skills/spec-principles/SKILL.md"])

    def test_skill_codex_tree_is_not_applicable(self):
        self.assertEqual(expected_paths(_skill("align"), CODEX, ROOT), [])

    def test_agent_github_path(self):
        paths = expected_paths(_agent("spec-author"), GITHUB, ROOT)
        self.assertEqual(paths, [ROOT / ".github/agents/spec-author.agent.md"])

    def test_agent_codex_path(self):
        paths = expected_paths(_agent("spec-author"), CODEX, ROOT)
        self.assertEqual(paths, [ROOT / ".codex/agents/spec-author.toml"])

    def test_agent_agents_dir_tree_is_not_applicable(self):
        self.assertEqual(expected_paths(_agent("spec-author"), AGENTS_DIR, ROOT), [])


if __name__ == "__main__":
    unittest.main()
