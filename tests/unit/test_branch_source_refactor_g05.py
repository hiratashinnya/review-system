"""G-05 branch_source refactor regression contracts."""

import subprocess
import unittest
from unittest.mock import patch
from branch_source import (BranchSourceError, GitHubBranchClient, NewBranchRequest,
                           create_branch, parse_new_branch_args, verify_branch_source)
from branch_source import policy
from branch_source.github_client import GitHubBranchClient as HttpClient
from branch_source.model import BranchSourceResult

OID = "a" * 40
OTHER = "b" * 40


class FakeApi:
    def __init__(self, pulls=None):
        self.pulls = pulls or []
        self.count = 0

    def repository(self, repository):
        return {"full_name": repository, "default_branch": "main"}

    def pull_request(self, repository, number):
        value = self.pulls[self.count]
        self.count += 1
        return value


def git_runner(calls, oid=OID, origin="https://github.com/owner/repo.git"):
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        out = origin if argv[1:3] == ["remote", "get-url"] else (
            oid if argv[1] == "rev-parse" else "")
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")
    return run


def pull(oid=OID):
    repo = {"full_name": "owner/repo"}
    return {"state": "open", "head": {"sha": oid, "repo": repo},
            "base": {"repo": repo}}


class G05Contracts(unittest.TestCase):
    def request(self, pr=None):
        return NewBranchRequest("stack-g/child", "owner/repo", "main", OID, pr)

    def test_facade_and_models_are_stable(self):
        self.assertIs(policy.GitHubBranchClient, HttpClient)
        self.assertIs(GitHubBranchClient, HttpClient)
        self.assertIs(policy.BranchSourceResult, BranchSourceResult)
        self.assertEqual(policy.POLICY_VERSION, "branch-source/1.0")

    def test_base_pr_rejects_non_ascii_and_huge_integers(self):
        for value in ("²", "１２", "9" * 5000, "0"):
            with self.subTest(value=value[:10]):
                with self.assertRaises(BranchSourceError) as caught:
                    parse_new_branch_args([
                        "stack-g/child", "--repository", "owner/repo",
                        "--base-ref", "main", "--base-oid", OID, "--base-pr", value])
                self.assertEqual(caught.exception.reason, "BRANCH_BASE_PR_INVALID")

    def test_default_branch_golden_argv_and_shell_false(self):
        calls = []
        result = create_branch(self.request(), api=FakeApi(), runner=git_runner(calls))
        self.assertEqual(result.source_kind, "default-branch")
        self.assertEqual([a for a, _ in calls], [
            ["git", "remote", "get-url", "origin"],
            ["git", "fetch", "--force", "--no-tags", "origin",
             "+refs/heads/main:refs/review-system/branch-source/default"],
            ["git", "rev-parse", "--verify",
             "refs/review-system/branch-source/default^{commit}"],
            ["git", "switch", "-c", "stack-g/child", OID]])
        self.assertTrue(all(kw["shell"] is False for _, kw in calls))

    def test_pr_changed_after_fetch_fails_before_branch_creation(self):
        calls = []
        api = FakeApi([pull(), pull(OTHER)])
        with self.assertRaises(BranchSourceError) as caught:
            create_branch(self.request(791), api=api, runner=git_runner(calls))
        self.assertEqual(caught.exception.reason, "BRANCH_BASE_PR_CHANGED")
        self.assertEqual(api.count, 2)
        self.assertEqual([argv[1] for argv, _ in calls], ["remote", "fetch"])

    def test_remote_mismatch_is_rejected_before_fetch(self):
        calls = []
        with self.assertRaises(BranchSourceError) as caught:
            verify_branch_source(self.request(), api=FakeApi(),
                runner=git_runner(calls, origin="https://github.com/other/repo.git"))
        self.assertEqual(caught.exception.reason, "BRANCH_REPOSITORY_MISMATCH")
        self.assertEqual(len(calls), 1)

    def test_policy_urllib_patch_point_remains_usable(self):
        with patch("branch_source.policy.urllib.request.urlopen",
                   side_effect=OSError("network offline")):
            with self.assertRaises(BranchSourceError) as caught:
                GitHubBranchClient("secret").repository("owner/repo")
        self.assertEqual(caught.exception.reason, "API_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
