"""G-04 public facade and pure-dispatch regression contracts."""
import io
import unittest
from unittest.mock import patch
from gitgate import cli
from gitgate.adopt import (
    AdoptBranchRequest, AdoptBranchResult, parse_adopt_branch_args,
    describe_local_ref_conflict, HOLDER_UNKNOWN,
)
from gitgate.cli_argv import build_git_argv as split_build_git_argv
from gitgate.cli_validation import GitgateError


class GitgateG04Contracts(unittest.TestCase):
    def test_every_pure_verb_uses_the_same_argv_builder(self):
        cases = {
            "status": ["status"],
            "add": ["add", "file name"],
            "push": ["push"],
            "branch-current": ["branch-current"],
            "fetch": ["fetch"],
            "diff": ["diff", "--stat", "main"],
            "log": ["log", "-n", "2", "--grep", "fix", "--oneline"],
        }
        for verb, args in cases.items():
            with self.subTest(verb=verb):
                self.assertEqual(cli.build_git_argv(args), split_build_git_argv(args))
                self.assertEqual(cli.build_git_argv(args)[0], "git")

    def test_policy_verbs_cannot_enter_pure_git_argv(self):
        for verb in ("adopt-branch", "worktree-release", "collect-worktree",
                     "worktree-forget", "worktree-sweep-abandoned"):
            with self.subTest(verb=verb):
                with self.assertRaises(GitgateError):
                    cli.build_git_argv([verb])

    def test_rejected_arg_never_runs_git_and_preserves_exit_code(self):
        with patch("gitgate.cli.subprocess.run") as run, \
             patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(cli.main(["diff", "--output=x"]), 2)
            run.assert_not_called()
            self.assertIn("gitgate:", stderr.getvalue())

    def test_adopt_schema_and_unknown_holder_message(self):
        oid = "a" * 40
        request = parse_adopt_branch_args([
            "topic/branch", "--repository", "example/repo",
            "--expected-oid", oid,
        ])
        self.assertIsInstance(request, AdoptBranchRequest)
        self.assertEqual(request.expected_oid, oid)
        self.assertEqual(AdoptBranchResult("topic/branch", "example/repo", oid, None).policy_version,
                         "branch-adopt/1.0")
        detail = describe_local_ref_conflict("topic/branch", holder_kind=HOLDER_UNKNOWN)
        self.assertIn("fail-close", detail)


if __name__ == "__main__":
    unittest.main()
