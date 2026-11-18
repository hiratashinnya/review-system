"""External GitHub mutations are mocked: never write an actual Issue."""
import json
import unittest
from unittest.mock import patch, Mock

from karte import ac_owner_github
from karte.errors import KarteUsageError


class GitHubOwnerAdapterTest(unittest.TestCase):
    def test_gh_api_changes_only_body_field_and_uses_stdin(self):
        result = Mock(returncode=0, stdout=json.dumps({"number": 801, "body": "new"}), stderr="")
        with patch.object(ac_owner_github.subprocess, "run", return_value=result) as run:
            self.assertEqual("new", ac_owner_github.issue(
                "hiratashinnya/review-system", 801, new_body="new"))
        command = run.call_args.args[0]
        self.assertEqual(["gh", "api", "repos/hiratashinnya/review-system/issues/801",
                          "--method", "PATCH", "--input", "-"], command)
        self.assertEqual({"body": "new"}, json.loads(run.call_args.kwargs["input"]))

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
                ac_owner_github.issue("hiratashinnya/review-system", 801, new_body="new")

    def test_rejects_invalid_repository_before_network(self):
        with patch.object(ac_owner_github.subprocess, "run") as run:
            with self.assertRaises(KarteUsageError):
                ac_owner_github.issue("other/repo?unsafe", 801)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
