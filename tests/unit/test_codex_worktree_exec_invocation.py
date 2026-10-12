"""argv の組立て・前置き・再帰起動の検知・依頼文ファイルの検査。"""

from pathlib import Path
import tempfile
import unittest

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.invocation import build_codex_argv, compose_prompt
from codex_worktree_exec.nesting_guard import NESTING_MARKER, refuse_nested_launch
from codex_worktree_exec.prompt_files import (
    MAX_PROMPT_BYTES,
    read_prompt,
    resolve_output_target,
)
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


class NestingGuardTests(unittest.TestCase):
    def test_markers_of_running_inside_codex_are_refused(self):
        for name in (NESTING_MARKER, "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED"):
            with self.subTest(name=name), self.assertRaises(CodexExecError) as caught:
                refuse_nested_launch({name: "1"})
            self.assertEqual(caught.exception.error_id, "CODEX_EXEC_NESTED")

    def test_plain_environment_passes(self):
        refuse_nested_launch({"PATH": "/usr/bin", "CODEX_SANDBOX": ""})


class PromptFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def assert_refused(self, call, error_id):
        with self.assertRaises(CodexExecError) as caught:
            call()
        self.assertEqual(caught.exception.error_id, error_id)

    def test_prompt_is_read_relative_to_cwd(self):
        (self.directory / "p.md").write_text("依頼本文\n", encoding="utf-8")
        self.assertEqual(read_prompt(Path("p.md"), self.directory), "依頼本文\n")

    def test_unusable_prompts_are_refused(self):
        bodies = {"empty.md": b"  \n", "binary.md": b"\xff\xfe", "large.md": b"x" * (MAX_PROMPT_BYTES + 1)}
        for name, data in bodies.items():
            (self.directory / name).write_bytes(data)
        (self.directory / "link.md").symlink_to(self.directory / "large.md")
        for name in (*bodies, "link.md", "absent.md"):
            with self.subTest(name=name):
                self.assert_refused(lambda: read_prompt(Path(name), self.directory), "CODEX_EXEC_PROMPT_UNREADABLE")

    def test_output_target_must_be_a_plain_path_in_an_existing_directory(self):
        self.assertEqual(
            resolve_output_target(Path("o.md"), self.directory), self.directory.resolve() / "o.md"
        )
        (self.directory / "dir").mkdir()
        (self.directory / "link.md").symlink_to(self.directory / "o.md")
        for name in ("dir", "link.md", "missing/o.md"):
            with self.subTest(name=name):
                self.assert_refused(lambda: resolve_output_target(Path(name), self.directory), "CODEX_EXEC_OUTPUT_INVALID")


if __name__ == "__main__":
    unittest.main()
