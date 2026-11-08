"""G-04 golden CLI argv, error/exit and adopt facade regression contracts."""
import io
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from gitgate import cli
from gitgate.adopt import (
    AdoptBranchRequest, AdoptBranchResult, parse_adopt_branch_args,
    describe_local_ref_conflict, HOLDER_UNKNOWN,
)
from gitgate.cli_validation import GitgateError


class GitgateG04Contracts(unittest.TestCase):
    def test_golden_argv_for_every_pure_verb(self):
        oid = "a" * 40
        cases = [
            (["status"], ["git", "status"]),
            (["add", "file name"], ["git", "add", "--", "file name"]),
            (["push"], ["git", "push", "-u", "origin", "HEAD"]),
            (["branch-current"], ["git", "branch", "--show-current"]),
            (["fetch"], ["git", "fetch", "--prune", "origin"]),
            (["diff", "--stat", "main"], ["git", "diff", "--stat", "main"]),
            (["log", "-n", "2", "--grep", "fix", "--oneline"],
             ["git", "log", "-n", "2", "--grep=fix", "--oneline"]),
            (["new-branch", "issue-317", "--repository", "example/repo",
              "--base-ref", "main", "--base-oid", oid],
             ["git", "switch", "-c", "issue-317", oid]),
        ]
        for args, expected in cases:
            with self.subTest(verb=args[0]):
                self.assertEqual(cli.build_git_argv(args), expected)
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(cli.build_git_argv(["commit", f.name]),
                             ["git", "commit", "-F", f.name])

    def test_policy_verbs_never_route_to_generic_git_runner(self):
        for verb in ("adopt-branch", "worktree-release", "collect-worktree",
                     "worktree-forget", "worktree-sweep-abandoned"):
            with self.subTest(verb=verb):
                with self.assertRaises(GitgateError):
                    cli.build_git_argv([verb])

    def test_plain_verb_preserves_returncode_and_shell_false(self):
        with patch("gitgate.cli.subprocess.run",
                   return_value=SimpleNamespace(returncode=13)) as run:
            self.assertEqual(cli.main(["status"]), 13)
        run.assert_called_once_with(["git", "status"], shell=False)

    def test_invalid_argv_does_not_execute_git(self):
        with patch("gitgate.cli.subprocess.run") as run, \
             patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(cli.main(["diff", "--output=x"]), 2)
            run.assert_not_called()
            self.assertIn("gitgate:", stderr.getvalue())

    def test_adopt_cli_preserves_stderr_and_skips_generic_runner(self):
        req = SimpleNamespace(branch_name="topic")
        result = SimpleNamespace(repository="owner/repo", expected_oid="a" * 40,
                                 pr=None, policy_version="branch-adopt/1.0")
        with patch("gitgate.cli.parse_adopt_branch_args", return_value=req), \
             patch("gitgate.cli.adopt_branch", return_value=result) as adopt, \
             patch("gitgate.cli.subprocess.run") as run, \
             patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(cli.main(["adopt-branch"]), 0)
        adopt.assert_called_once_with(req)
        run.assert_not_called()
        self.assertEqual(stderr.getvalue(), (
            f"gitgate: adopt-branch owner/repo@{'a' * 40} pr=- policy=branch-adopt/1.0\n"
            "gitgate: adopted existing branch 'topic' (checkout performed)\n"
        ))

    def test_adopt_public_types_and_fail_closed_diagnostic(self):
        oid = "a" * 40
        req = parse_adopt_branch_args(
            ["topic/branch", "--repository", "example/repo", "--expected-oid", oid])
        self.assertIsInstance(req, AdoptBranchRequest)
        self.assertEqual(req.expected_oid, oid)
        self.assertEqual(AdoptBranchResult("topic/branch", "example/repo", oid, None).policy_version,
                         "branch-adopt/1.0")
        self.assertIn("fail-close", describe_local_ref_conflict(
            "topic/branch", holder_kind=HOLDER_UNKNOWN))


if __name__ == "__main__":
    unittest.main()
