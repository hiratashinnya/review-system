"""GitHub API credential resolver の優先順位と秘密非露出。"""

import subprocess
import unittest

from blocker_gate.auth import (
    GH_AUTH_TIMEOUT_SECONDS,
    github_api_failure_reason,
    resolve_github_token,
)


class Completed:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


class GitHubTokenResolverTests(unittest.TestCase):
    def test_common_api_failure_classification(self):
        cases = (
            (401, {}, "API_PERMISSION"),
            (403, {}, "API_PERMISSION"),
            (403, {"X-RateLimit-Remaining": "0"}, "API_UNAVAILABLE"),
            (403, {"x-ratelimit-remaining": "0"}, "API_UNAVAILABLE"),
            (429, {}, "API_UNAVAILABLE"),
            (503, {}, "API_UNAVAILABLE"),
            (404, {}, None),
        )
        for status, headers, expected in cases:
            with self.subTest(status=status, headers=headers):
                self.assertEqual(
                    github_api_failure_reason(status, headers), expected
                )

    def test_environment_priority_avoids_gh(self):
        def unexpected(*args, **kwargs):
            raise AssertionError("environment credential must avoid gh")

        self.assertEqual(
            resolve_github_token(
                environ={"GH_TOKEN": "gh-secret", "GITHUB_TOKEN": "actions-secret"},
                runner=unexpected,
            ),
            "gh-secret",
        )
        self.assertEqual(
            resolve_github_token(
                environ={"GH_TOKEN": "", "GITHUB_TOKEN": "actions-secret"},
                runner=unexpected,
            ),
            "actions-secret",
        )

    def test_gh_fallback_has_fixed_safe_process_contract(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return Completed("credential-from-gh\n")

        self.assertEqual(
            resolve_github_token(environ={}, runner=runner), "credential-from-gh"
        )
        argv, kwargs = calls[0]
        self.assertEqual(
            argv, ["gh", "auth", "token", "--hostname", "github.com"]
        )
        self.assertIs(kwargs["shell"], False)
        self.assertIs(kwargs["capture_output"], True)
        self.assertIs(kwargs["text"], True)
        self.assertIs(kwargs["check"], False)
        self.assertEqual(kwargs["timeout"], GH_AUTH_TIMEOUT_SECONDS)
        self.assertLessEqual(kwargs["timeout"], 5)

    def test_gh_missing_timeout_empty_and_abnormal_fall_back_to_anonymous(self):
        secret = "must-not-escape-from-gh-error"

        def missing(*args, **kwargs):
            raise FileNotFoundError(secret)

        def timeout(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=secret)

        runners = (
            missing,
            timeout,
            lambda *args, **kwargs: Completed(""),
            lambda *args, **kwargs: Completed("ignored-secret", returncode=1),
            lambda *args, **kwargs: Completed(None),
        )
        for runner in runners:
            with self.subTest(runner=runner):
                self.assertIsNone(resolve_github_token(environ={}, runner=runner))


if __name__ == "__main__":
    unittest.main()
