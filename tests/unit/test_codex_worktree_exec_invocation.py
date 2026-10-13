"""Codex の argv 組立てと依頼本文に付ける前置き。"""

from pathlib import Path
import unittest

from codex_worktree_exec.invocation import build_codex_argv, compose_prompt
from codex_worktree_exec.request import ExecRequest


def make_request(**overrides):
    values = dict(
        role="issue-fixer", worktree=Path("wt"), prompt_file=Path("p.md"),
        output_file=Path("o.md"), model="gpt-6-sol", reasoning_effort="xhigh",
        timeout_seconds=540,
    )
    values.update(overrides)
    return ExecRequest(**values)


class InvocationTests(unittest.TestCase):
    def test_argv_selects_the_role_profile_and_the_callers_model(self):
        argv = build_codex_argv(make_request(), Path("/w/t"), Path("/w/t/tmp/o.md"), "codex")
        self.assertEqual(argv, [
            "codex", "exec", "-C", "/w/t",
            "-c", 'default_permissions="issue-fixer"',
            "-m", "gpt-6-sol",
            "-c", 'model_reasoning_effort="xhigh"',
            "--output-last-message", "/w/t/tmp/o.md",
            "-",
        ])

    def test_argv_never_bypasses_the_sandbox_or_approvals(self):
        argv = build_codex_argv(make_request(), Path("/w"), Path("/w/o.md"))
        for forbidden in ("--dangerously-bypass-approvals-and-sandbox", "--full-auto", "-s", "--sandbox"):
            self.assertNotIn(forbidden, argv)

    def test_prompt_starts_with_the_no_delegation_preamble(self):
        prompt = compose_prompt("issue-implementer", Path("/w/t"), "テストを直す")
        self.assertTrue(prompt.startswith("[codex_worktree_exec の前置き]"))
        self.assertIn("issue-implementer", prompt)
        self.assertIn("/w/t", prompt)
        self.assertIn("委譲はしない", prompt)
        self.assertIn("commit・push", prompt)
        self.assertTrue(prompt.endswith("[依頼]\nテストを直す"))


if __name__ == "__main__":
    unittest.main()
