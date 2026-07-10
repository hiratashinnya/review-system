"""asset_parity.trees — ツリー別命名規則・skill/prompt 振り分けの契約。"""

import unittest
from pathlib import Path

from asset_parity.inventory import AGENT, MODE_ORCHESTRATOR, MODE_PRINCIPLE, MODE_SKILL, SKILL, Asset
from asset_parity.trees import AGENTS_DIR, CODEX, GITHUB, applicable_trees, expected_paths


ROOT = Path("/repo")


def _skill(name, mode=MODE_SKILL):
    return Asset(name=name, kind=SKILL, mode=mode, canonical_path=ROOT / ".claude/skills" / name / "SKILL.md")


def _agent(name):
    return Asset(name=name, kind=AGENT, mode=None, canonical_path=ROOT / ".claude/agents" / f"{name}.md")


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

    def test_principle_skill_github_is_structurally_na(self):
        paths = expected_paths(_skill("spec-principles", MODE_PRINCIPLE), GITHUB, ROOT)
        self.assertEqual(paths, [])

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
