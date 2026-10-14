"""asset_parity.trees — ツリー別命名規則・skill/prompt 振り分けの契約。"""

import tempfile
import unittest
from pathlib import Path

from asset_parity.copilot_paths import copilot_instructions_path, copilot_skill_path, inline_slot_path
from asset_parity.inventory import AGENT, MODE_ORCHESTRATOR, MODE_PRINCIPLE, MODE_SKILL, SKILL, Asset
from asset_parity.trees import AGENTS_DIR, CODEX, GITHUB, applicable_trees, expected_paths

from tests.unit.asset_parity_fixtures import generated_instructions_text, principles_marker_line

ROOT = Path("/repo")


def _skill(name, mode=MODE_SKILL):
    return Asset(name=name, kind=SKILL, mode=mode, parity_seed_path=ROOT / ".claude/skills" / name / "SKILL.md")


def _agent(name):
    return Asset(name=name, kind=AGENT, mode=None, parity_seed_path=ROOT / ".claude/agents" / f"{name}.md")


def _write_instructions(root, text):
    instructions = copilot_instructions_path(root)
    instructions.parent.mkdir(parents=True)
    instructions.write_text(text, encoding="utf-8")


def _write_generated(root, *, header_skill, body_lines=()):
    # header/marker shapes are pinned to guidance_sync in test_asset_parity_inlining_marker
    _write_instructions(root, generated_instructions_text(
        header_skill=header_skill, body_lines=body_lines,
    ))


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
            _write_generated(
                root, header_skill="spec-principles",
                body_lines=(principles_marker_line("some-principle"),),
            )
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self.assertEqual(expected_paths(asset, GITHUB, root), [])

    def _assert_uninlined_expects_only_inline_slot(self, root, asset):
        paths = expected_paths(asset, GITHUB, root)
        self.assertEqual(paths, [inline_slot_path(asset.name, root)])
        # The slot is never a file, and a plain skill file is not among the candidates.
        self.assertFalse(any(p.is_file() for p in paths))
        self.assertNotIn(copilot_skill_path(asset.name, root), paths)

    def test_uninlined_principle_skill_github_expects_only_inline_slot(self):
        # instructions exist but name only another skill: this one is not inlined
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_generated(
                root, header_skill="spec-principles",
                body_lines=(principles_marker_line("some-other-principle"),),
            )
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self._assert_uninlined_expects_only_inline_slot(root, asset)

    def test_marker_only_in_generated_header_does_not_count_as_inlined(self):
        # guidance_sync writes the principles-source marker into the header whether or not the
        # body carries the principle, so the header marker alone is no evidence of inlining.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_generated(root, header_skill="some-principle")
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self._assert_uninlined_expects_only_inline_slot(root, asset)

    def test_directory_at_instructions_path_never_makes_inline_slot_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            slot = inline_slot_path(asset.name, root)
            copilot_instructions_path(root).mkdir(parents=True)
            Path(str(slot)).write_text("not the inlined text", encoding="utf-8")
            self.assertTrue(Path(str(slot)).is_file())  # a real file does sit at the slot's path
            self._assert_uninlined_expects_only_inline_slot(root, asset)

    def test_principle_skill_without_instructions_file_expects_only_inline_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self._assert_uninlined_expects_only_inline_slot(root, asset)

    def test_uninlined_principle_skill_with_plain_skill_file_is_still_not_satisfied(self):
        # asset-lateral-deploy routes `user-invocable: false` to Instructions, never to a skill:
        # a plain Copilot skill file for it is a misplacement, not a mirror.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_generated(
                root, header_skill="spec-principles",
                body_lines=(principles_marker_line("some-other-principle"),),
            )
            stray = copilot_skill_path("some-principle", root)
            stray.parent.mkdir(parents=True)
            stray.write_text("---\nname: some-principle\n---\n", encoding="utf-8")
            asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
            self.assertTrue(stray.is_file())
            self._assert_uninlined_expects_only_inline_slot(root, asset)

    def test_incomplete_or_malformed_marker_does_not_count_as_inlined(self):
        good_sha = "ab" * 32
        base = "<!-- principles-source: .ai/skills/some-principle/SKILL.md;"
        malformed = {
            "prefix only": base,
            "no sha256 field": f"{base} -->",
            "sha256 not hex digits": f"{base} sha256: 0 -->",
            "sha256 too short": f"{base} sha256: {good_sha[:-1]} -->",
            "sha256 too long": f"{base} sha256: {good_sha}0 -->",
            "comment not closed": f"{base} sha256: {good_sha}",
            "trailing text": f"{base} sha256: {good_sha} --> trailing",
            "other skill name": f"<!-- principles-source: .ai/skills/some-principle-x/SKILL.md; "
                                f"sha256: {good_sha} -->",
        }
        for label, line in malformed.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                # the header carries a valid marker for the same skill; only the body line varies
                _write_generated(root, header_skill="some-principle", body_lines=(line,))
                asset = Asset("some-principle", SKILL, MODE_PRINCIPLE, root / "seed.md")
                self._assert_uninlined_expects_only_inline_slot(root, asset)

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
