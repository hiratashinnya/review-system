import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.triager_dispatch import dispatch
from codex_worktree_exec.triager_instructions import triager_instructions
from triage_policy.evidence import PHASE_EVIDENCE, required_categories

CLAUSE = re.compile(r"evidence \(nonempty ([a-z_, ]+) strings\)")


def listed(text):
    match = CLAUSE.search(text)
    assert match, "evidence clause missing"
    return tuple(match.group(1).split(", "))


class TriagerInstructionsTest(unittest.TestCase):
    def test_every_phase_lists_exactly_the_table_categories(self):
        for phase in PHASE_EVIDENCE:
            with self.subTest(phase=phase):
                self.assertEqual(listed(triager_instructions(phase)), required_categories(phase))

    def test_verification_design_omits_design_and_others_keep_it(self):
        self.assertNotIn("design", listed(triager_instructions("verification_design")))
        for phase in set(PHASE_EVIDENCE) - {"verification_design"}:
            with self.subTest(phase=phase):
                self.assertIn("design", listed(triager_instructions(phase)))

    def test_unknown_phase_has_no_instructions(self):
        for phase in ("plan", "", None):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                triager_instructions(phase)

    def test_dispatch_sends_the_table_derived_instructions_for_each_phase(self):
        for phase in PHASE_EVIDENCE:
            with self.subTest(phase=phase):
                prompts = self.launched_prompts(phase)
                self.assertEqual(len(prompts), 1)
                self.assertEqual(listed(prompts[0]), required_categories(phase))
        self.assertNotIn("design", listed(self.launched_prompts("verification_design")[0]))

    def launched_prompts(self, phase):
        prompts = []
        def run(argv, prompt, **kwargs):
            prompts.append(prompt)
            return 2
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "tmp").mkdir()
            request = SimpleNamespace(output_file=Path("tmp/out.json"), timeout_seconds=30, model="m",
                                      reasoning_effort="high", role="finding-triager")
            validated = ({}, [b"k" * 32, b"c" * 32], b"", b"", "PROMPT", {"phase": phase})
            with patch("codex_worktree_exec.triager_dispatch.validate_binding", return_value=validated), \
                 patch("codex_worktree_exec.triager_dispatch.run_codex", side_effect=run):
                with self.assertRaises(CodexExecError):
                    dispatch(request, root, root, {}, "codex")
        return prompts


if __name__ == "__main__":
    unittest.main()
