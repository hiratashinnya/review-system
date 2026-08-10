import subprocess
import tempfile
import unittest
from pathlib import Path

from pr_merge_gate.classifier import classify_pre_use, repository_from_cwd


def bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class PreUseClassifierTests(unittest.TestCase):
    def test_direct_wrapped_and_global_repo_cli_are_bound(self):
        cases = (
            ("gh -R example/repo pr merge 12 --squash --match-head-commit " + "a" * 40, "cli-direct"),
            ("rtk proxy command -- gh pr merge 12 --repo example/repo --rebase", "cli-wrapped"),
        )
        for command, transport in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(classified.kind, "merge")
                self.assertEqual(classified.operation.repository, "example/repo")
                self.assertEqual(classified.operation.pr_number, 12)
                self.assertEqual(classified.operation.transport, transport)

    def test_method_omission_auto_merge_and_shell_bypass_fail_close(self):
        cases = (
            ("gh -R example/repo pr merge 12", "error", "MERGE_METHOD_UNKNOWN"),
            ("gh -R example/repo pr merge 12 --squash --auto", "block", "AUTO_MERGE_DENIED"),
            ("gh -R example/repo pr merge 12 --squash; true", "error", "CLASSIFIER_UNKNOWN"),
        )
        for command, kind, reason in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual((classified.kind, classified.reason), (kind, reason))

    def test_token_normalization_closes_quote_escape_and_endpoint_bypasses(self):
        cases = (
            'gh -R example/repo pr "merge" 12 --squash',
            "gh -R example/repo pr mer\\ge 12 --squash",
            'gh api -X PUT repos/example/repo/pulls/12/mer""ge -f merge_method=squash',
        )
        for command in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(classified.kind, "merge")

    def test_unknown_alias_wrapper_and_merge_like_extension_fail_close(self):
        cases = (
            "gh alias exec land pr merge 12 --squash",
            "custom-wrapper gh -R example/repo pr merge 12 --squash",
            "gh extension exec land example/repo#12",
        )
        for command in cases:
            with self.subTest(command=command):
                classified = classify_pre_use(bash(command))
                self.assertEqual(
                    (classified.kind, classified.reason),
                    ("error", "CLASSIFIER_UNKNOWN"),
                )

    def test_quoted_shell_punctuation_does_not_create_a_false_bypass(self):
        classified = classify_pre_use(
            bash('gh -R example/repo pr merge 12 --squash --body "text; still one arg"')
        )
        self.assertEqual(classified.kind, "merge")

    def test_rest_merge_endpoint_and_connector_are_bound(self):
        rest = classify_pre_use(
            bash(
                "gh api -X PUT repos/example/repo/pulls/12/merge "
                "-f merge_method=squash -f sha=" + "b" * 40
            )
        )
        self.assertEqual((rest.kind, rest.operation.transport), ("merge", "rest"))
        connector = classify_pre_use(
            {
                "tool_name": "mcp__codex_apps__github_merge_pull_request",
                "tool_input": {
                    "repository_full_name": "example/repo",
                    "pr_number": 12,
                    "merge_method": "merge",
                    "commit_title": "title",
                    "commit_message": "fixes #7",
                    "expected_head_sha": "c" * 40,
                },
            }
        )
        self.assertEqual((connector.kind, connector.operation.transport), ("merge", "connector"))

    def test_connector_auto_merge_and_unknown_merge_tool_are_denied(self):
        auto = classify_pre_use(
            {
                "tool_name": "mcp__codex_apps__github_enable_auto_merge",
                "tool_input": {"repository_full_name": "example/repo", "pr_number": 12},
            }
        )
        unknown = classify_pre_use(
            {"tool_name": "mcp__future__merge_pull_request", "tool_input": {}}
        )
        self.assertEqual((auto.kind, auto.reason), ("block", "AUTO_MERGE_DENIED"))
        self.assertEqual((unknown.kind, unknown.reason), ("error", "CLASSIFIER_UNKNOWN"))

    def test_non_merge_tool_is_outside_this_gate(self):
        self.assertIsNone(classify_pre_use(bash("gh issue view 12")))
        self.assertIsNone(classify_pre_use({"tool_name": "Read", "tool_input": {"path": "x"}}))


class RepositoryBindingTests(unittest.TestCase):
    def test_repository_from_cwd_requires_exact_worktree_and_github_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            def runner(argv, **kwargs):
                if argv == ["git", "rev-parse", "--show-toplevel"]:
                    output = str(root) + "\n"
                else:
                    self.assertEqual(argv, ["git", "remote", "get-url", "origin"])
                    output = "git@github.com:example/repo.git\n"
                return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")

            actual = repository_from_cwd(
                {"cwd": str(root)}, cwd=root, runner=runner
            )
            self.assertEqual(actual, "example/repo")


if __name__ == "__main__":
    unittest.main()
