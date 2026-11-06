"""整数引数の拒否契約を CLI と branch-source ごとに検証する。"""

import contextlib
import io
import unittest

from branch_source import BranchSourceError, parse_new_branch_args
from codex_worktree_exec.arguments import parse_request
from codex_worktree_exec.cli import main


class IntegerArgumentTests(unittest.TestCase):
    def test_timeout_invalid_values_are_refused_by_cli(self):
        for value in ("²", "５", "9" * 5000):
            with self.subTest(value=value[:10]):
                stderr = io.StringIO()
                args = ["--role", "issue-fixer", "-C", ".", "--prompt-file", "p",
                        "--output-file", "o", "--model", "gpt-6-sol",
                        "--reasoning-effort", "high", "--timeout-seconds", value]
                with contextlib.redirect_stderr(stderr):
                    code = main(args)
                self.assertEqual(code, 2)
                self.assertEqual(len(stderr.getvalue().splitlines()), 1)
                self.assertIn("CODEX_EXEC_TIMEOUT_INVALID", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_timeout_ascii_value_is_accepted(self):
        args = ["--role", "issue-fixer", "-C", ".", "--prompt-file", "p",
                "--output-file", "o", "--model", "gpt-6-sol",
                "--reasoning-effort", "high", "--timeout-seconds", "30"]
        self.assertEqual(parse_request(args).timeout_seconds, 30)

    def test_base_pr_values(self):
        args = ["issue-719", "--repository", "example/repo", "--base-ref", "main",
                "--base-oid", "a" * 40, "--base-pr"]
        for value in ("²", "５", "9" * 5000):
            with self.subTest(value=value[:10]):
                with self.assertRaisesRegex(BranchSourceError, "BRANCH_BASE_PR_INVALID"):
                    parse_new_branch_args(args + [value])
        self.assertEqual(parse_new_branch_args(args + ["5"]).base_pr, 5)


if __name__ == "__main__":
    unittest.main()
