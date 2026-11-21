"""GitHub API is mocked: explicit frozen host on every operation."""
import json
import os
import unittest
from unittest.mock import patch, Mock

from karte import ac_owner_github
from karte.errors import KarteUsageError


class GitHubOwnerAdapterTest(unittest.TestCase):
    def test_explicit_host_wins_over_gh_host_for_read_and_patch(self):
        for host, env_host in (("github.com", "unrelated.corp.example"),
                               ("git.corp.example", "github.com")):
            with self.subTest(host=host), patch.dict(os.environ, {"GH_HOST": env_host}):
                result = Mock(returncode=0, stdout=json.dumps({"number": 801, "body": "new"}), stderr="")
                with patch.object(ac_owner_github.subprocess, "run", return_value=result) as run:
                    self.assertEqual("new", ac_owner_github.issue(
                        host, "hiratashinnya/review-system", 801))
                    self.assertEqual("new", ac_owner_github.issue(
                        host, "hiratashinnya/review-system", 801, new_body="new"))
                calls = run.call_args_list
                endpoint = "repos/hiratashinnya/review-system/issues/801"
                self.assertEqual(["gh", "api", "--hostname", host, endpoint], calls[0].args[0])
                self.assertEqual(["gh", "api", "--hostname", host, endpoint,
                                  "--method", "PATCH", "--input", "-"], calls[1].args[0])
                self.assertEqual({"body": "new"}, json.loads(calls[1].kwargs["input"]))

    def test_rejects_pr_target_invalid_response_and_git_error(self):
        for response in (
            Mock(returncode=0, stdout=json.dumps({
                "number": 801, "body": "body", "pull_request": {}}), stderr=""),
            Mock(returncode=0, stdout=json.dumps({"number": 802, "body": "body"}), stderr=""),
            Mock(returncode=1, stdout="", stderr="denied"),
            Mock(returncode=0, stdout="not-json", stderr=""),
        ):
            with self.subTest(response=response), patch.object(
                ac_owner_github.subprocess, "run", return_value=response
            ), self.assertRaises(KarteUsageError):
                ac_owner_github.issue("github.com", "hiratashinnya/review-system", 801, new_body="new")

    def test_bad_host_and_repository_never_call_git_cli(self):
        with patch.object(ac_owner_github.subprocess, "run") as run:
            for host, repo in (("evil.example/path", "owner/repo"),
                               ("evil..example", "owner/repo"),
                               ("github.com", "other/repo?unsafe")):
                with self.subTest(host=host, repo=repo), self.assertRaises(KarteUsageError):
                    ac_owner_github.issue(host, repo, 801)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
