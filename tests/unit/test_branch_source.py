"""Issue #317 branch-source policy unit/negative tests。"""

import io
import json
import subprocess
import traceback
import unittest
import urllib.error
from unittest.mock import patch

from branch_source import (
    BranchSourceError,
    GitHubBranchClient,
    NewBranchRequest,
    create_branch,
    parse_new_branch_args,
    verify_branch_source,
)


OID = "a" * 40
OTHER = "b" * 40


class ApiResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def api_opener(payloads, requests):
    remaining = list(payloads)

    def open_url(request, timeout):
        requests.append(request)
        response = remaining.pop(0)
        if isinstance(response, BaseException):
            raise response
        return ApiResponse(response)

    return open_url


def http_error(status, headers=None, body=b"{}"):
    return urllib.error.HTTPError(
        "https://api.github.com/fixed",
        status,
        "safe status",
        {} if headers is None else headers,
        io.BytesIO(body),
    )


class FakeApi:
    def __init__(self, pull=None, repository=None, events=None):
        self.pull = pull
        self.repository_data = repository
        self.events = [] if events is None else events
        self.pull_calls = 0

    def repository(self, repository):
        return self.repository_data or {"full_name": repository, "default_branch": "main"}

    def pull_request(self, repository, number):
        if self.pull is None:
            raise AssertionError("pull_request must not be called")
        self.events.append("api-read")
        index = self.pull_calls
        self.pull_calls += 1
        if isinstance(self.pull, list):
            return self.pull[min(index, len(self.pull) - 1)]
        return self.pull


def runner_for(observed=OID, calls=None, events=None):
    captured = [] if calls is None else calls

    def run(argv, **kwargs):
        captured.append(argv)
        if events is not None and argv[:2] == ["git", "fetch"]:
            events.append("fetch")
        if argv[:4] == ["git", "remote", "get-url", "origin"]:
            out = "https://github.com/example/repo.git\n"
        elif argv[:3] == ["git", "rev-parse", "--verify"]:
            out = observed + "\n"
        else:
            out = ""
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")

    return run


class BranchSourceTests(unittest.TestCase):
    def request(self, base_pr=None):
        return NewBranchRequest("issue-317", "example/repo", "main", OID, base_pr)

    def test_parse_requires_explicit_repository_ref_and_oid(self):
        parsed = parse_new_branch_args([
            "issue-317", "--repository", "example/repo", "--base-ref", "main",
            "--base-oid", OID,
        ])
        self.assertEqual(parsed, self.request())
        with self.assertRaises(BranchSourceError):
            parse_new_branch_args(["issue-317"])

    def test_branch_ref_and_option_injection_are_rejected(self):
        cases = (
            ["--help", "--repository", "example/repo", "--base-ref", "main", "--base-oid", OID],
            ["issue-317", "--repository", "example/repo", "--base-ref", "main:evil", "--base-oid", OID],
            ["issue-317", "--repository", "example/repo", "--base-ref", "main", "--base-oid", OID, "--upload-pack=evil", "x"],
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises(BranchSourceError):
                parse_new_branch_args(args)

    def test_default_branch_uses_fresh_origin_exact_oid(self):
        calls = []
        result = create_branch(self.request(), api=FakeApi(), runner=runner_for(calls=calls))
        self.assertEqual(result.source_kind, "default-branch")
        self.assertIn([
            "git", "fetch", "--force", "--no-tags", "origin",
            "+refs/heads/main:refs/review-system/branch-source/default",
        ], calls)
        self.assertEqual(calls[-1], ["git", "switch", "-c", "issue-317", OID])

    def test_api_default_ref_injection_fails_before_fetch(self):
        calls = []
        api = FakeApi(repository={
            "full_name": "example/repo",
            "default_branch": "main:refs/heads/evil",
        })
        with self.assertRaisesRegex(BranchSourceError, "BRANCH_DEFAULT_REF_INVALID"):
            verify_branch_source(self.request(), api=api, runner=runner_for(calls=calls))
        self.assertFalse(any(call[:2] == ["git", "fetch"] for call in calls))

    def test_default_oid_mismatch_denies_before_switch(self):
        calls = []
        with self.assertRaisesRegex(BranchSourceError, "BRANCH_BASE_OID_MISMATCH"):
            create_branch(self.request(), api=FakeApi(), runner=runner_for(OTHER, calls))
        self.assertFalse(any(call[:3] == ["git", "switch", "-c"] for call in calls))

    def test_same_repo_open_pr_exact_head_is_allowed(self):
        events = []
        pull = {
            "state": "open",
            "head": {"sha": OID, "repo": {"full_name": "example/repo"}},
            "base": {"repo": {"full_name": "example/repo"}},
        }
        api = FakeApi(pull, events=events)
        result = verify_branch_source(
            self.request(42), api=api, runner=runner_for(events=events)
        )
        self.assertEqual(result.source_kind, "same-repository-open-pr")
        self.assertEqual(events, ["api-read", "fetch", "api-read"])
        self.assertEqual(api.pull_calls, 2)

    def test_env_unset_gh_credential_allows_default_branch(self):
        secret = "gh-default-credential-secret"
        requests = []
        gh_result = subprocess.CompletedProcess(
            ["gh", "auth", "token"], 0, stdout=secret + "\n", stderr=""
        )
        with patch.dict("os.environ", {}, clear=True), patch(
            "blocker_gate.auth.subprocess.run", return_value=gh_result
        ), patch(
            "branch_source.policy.urllib.request.urlopen",
            side_effect=api_opener(
                [{"full_name": "example/repo", "default_branch": "main"}],
                requests,
            ),
        ):
            result = verify_branch_source(self.request(), runner=runner_for())

        self.assertEqual(result.source_kind, "default-branch")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer " + secret)
        self.assertNotIn(secret, repr(result))

    def test_env_unset_gh_credential_authenticates_all_stacked_reads(self):
        secret = "gh-stacked-credential-secret"
        requests = []
        pull = {
            "state": "open",
            "head": {"sha": OID, "repo": {"full_name": "example/repo"}},
            "base": {"repo": {"full_name": "example/repo"}},
        }
        gh_result = subprocess.CompletedProcess(
            ["gh", "auth", "token"], 0, stdout=secret + "\n", stderr=""
        )
        with patch.dict("os.environ", {}, clear=True), patch(
            "blocker_gate.auth.subprocess.run", return_value=gh_result
        ), patch(
            "branch_source.policy.urllib.request.urlopen",
            side_effect=api_opener(
                [
                    {"full_name": "example/repo", "default_branch": "main"},
                    pull,
                    pull,
                ],
                requests,
            ),
        ):
            result = verify_branch_source(self.request(42), runner=runner_for())

        self.assertEqual(result.source_kind, "same-repository-open-pr")
        self.assertEqual(len(requests), 3)
        self.assertEqual(
            [request.get_header("Authorization") for request in requests],
            ["Bearer " + secret] * 3,
        )
        self.assertNotIn(secret, repr(result))

    def test_gh_failure_falls_back_to_anonymous_read(self):
        requests = []
        gh_result = subprocess.CompletedProcess(
            ["gh", "auth", "token"], 1, stdout="ignored", stderr="safe"
        )
        with patch.dict("os.environ", {}, clear=True), patch(
            "blocker_gate.auth.subprocess.run", return_value=gh_result
        ), patch(
            "branch_source.policy.urllib.request.urlopen",
            side_effect=api_opener(
                [{"full_name": "example/repo", "default_branch": "main"}],
                requests,
            ),
        ):
            result = verify_branch_source(self.request(), runner=runner_for())

        self.assertEqual(result.source_kind, "default-branch")
        self.assertIsNone(requests[0].get_header("Authorization"))

    def test_rate_limit_and_permission_failures_use_common_reasons(self):
        cases = (
            (403, {"X-RateLimit-Remaining": "0"}, "API_UNAVAILABLE"),
            (403, {}, "API_PERMISSION"),
            (401, {}, "API_PERMISSION"),
        )
        for status, headers, reason in cases:
            secret = f"secret-{status}-{reason}"
            with self.subTest(status=status, headers=headers), patch(
                "branch_source.policy.urllib.request.urlopen",
                side_effect=http_error(status, headers, secret.encode("utf-8")),
            ):
                with self.assertRaises(BranchSourceError) as caught:
                    GitHubBranchClient(secret).repository("example/repo")
            self.assertEqual(caught.exception.reason, reason)
            rendered = "".join(
                traceback.format_exception(
                    type(caught.exception), caught.exception, caught.exception.__traceback__
                )
            )
            self.assertNotIn(secret, str(caught.exception))
            self.assertNotIn(secret, rendered)

    def test_failed_gh_and_anonymous_api_fail_close_before_fetch(self):
        secret = "anonymous-api-response-secret"
        calls = []
        gh_result = subprocess.CompletedProcess(
            ["gh", "auth", "token"], 1, stdout="", stderr=""
        )
        with patch.dict("os.environ", {}, clear=True), patch(
            "blocker_gate.auth.subprocess.run", return_value=gh_result
        ), patch(
            "branch_source.policy.urllib.request.urlopen",
            side_effect=http_error(503, body=secret.encode("utf-8")),
        ):
            with self.assertRaises(BranchSourceError) as caught:
                verify_branch_source(self.request(), runner=runner_for(calls=calls))

        self.assertEqual(caught.exception.reason, "API_UNAVAILABLE")
        self.assertNotIn(secret, str(caught.exception))
        self.assertFalse(any(call[:2] == ["git", "fetch"] for call in calls))
        self.assertFalse(any(call[:3] == ["git", "switch", "-c"] for call in calls))

    def test_closed_cross_repo_and_fetched_mismatch_fail_close(self):
        cases = [
            ({"state": "closed"}, OID, "BRANCH_BASE_PR_NOT_OPEN"),
            ({
                "state": "open", "head": {"sha": OID, "repo": {"full_name": "fork/repo"}},
                "base": {"repo": {"full_name": "example/repo"}},
            }, OID, "BRANCH_BASE_PR_CROSS_REPOSITORY"),
            ({
                "state": "open", "head": {"sha": OID, "repo": {"full_name": "example/repo"}},
                "base": {"repo": {"full_name": "example/repo"}},
            }, OTHER, "BRANCH_PR_HEAD_MISMATCH"),
        ]
        for pull, observed, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(BranchSourceError, reason):
                    verify_branch_source(
                        self.request(42), api=FakeApi(pull), runner=runner_for(observed)
                    )

    def test_stacked_pr_change_during_fetch_fails_close(self):
        before = {
            "state": "open",
            "head": {"sha": OID, "repo": {"full_name": "example/repo"}},
            "base": {"repo": {"full_name": "example/repo"}},
        }
        after = {
            **before,
            "head": {"sha": OTHER, "repo": {"full_name": "example/repo"}},
        }
        with self.assertRaisesRegex(BranchSourceError, "BRANCH_BASE_PR_CHANGED"):
            verify_branch_source(
                self.request(42), api=FakeApi([before, after]), runner=runner_for()
            )


if __name__ == "__main__":
    unittest.main()
