"""gh 境界のページング、応答、失敗分類をオフラインで試す。"""

import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from karte import finding_handoff_github as gh
from karte.errors import KarteNotFound, KarteUsageError
from karte.finding_handoff_errors import FindingHandoffError
def reply(value, headers=""):
    return SimpleNamespace(stdout="HTTP/2.0 200 OK\n" + headers + "\n\n" + json.dumps(value))
def comment():
    return {"body": "body", "html_url": "https://github.com/o/r/issues/9#issuecomment-1",
            "created_at": "2026-01-01T00:00:00Z", "user": {"login": "me"},
            "issue_url": "https://api.github.com/repos/o/r/issues/9"}
def issue():
    return {"state": "open", "state_reason": None, "html_url": "https://github.com/o/r/issues/9",
            "repository_url": "https://api.github.com/repos/o/r", "number": 9, "locked": False}


class GhTest(unittest.TestCase):
    def setUp(self):
        guard = patch("subprocess.run", side_effect=AssertionError("実コマンド禁止"))
        guard.start()
        self.addCleanup(guard.stop)

    def test_paginate_and_timeout(self):
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return reply([], 'Link: <https://api.github.com/next>; rel="next"') if len(calls) == 1 else reply([comment()])
        self.assertEqual([comment()], gh.list_comments("o/r#9", run))
        self.assertIn("page=2", calls[1][0][-1])
        for _, kwargs in calls:
            self.assertEqual(30, kwargs["timeout"])
            self.assertFalse(kwargs["shell"])

    def test_page_failure_propagates(self):
        def run(argv, **kwargs):
            if "&page=1" in argv[-1]:
                return reply([], 'Link: <next>; rel="next"')
            raise subprocess.CalledProcessError(1, argv, stderr="HTTP 500")
        with self.assertRaises(FindingHandoffError) as error:
            gh.list_comments("o/r#9", run)
        self.assertEqual("server", error.exception.kind)

    def test_failures(self):
        cases = [("HTTP 401", "authentication"), ("To get started, run: gh auth login", "authentication"),
                 ("HTTP 403\nx-ratelimit-remaining: 0", "rate_limit"),
                 ("HTTP 403\nretry-after: 10", "rate_limit"), ("HTTP 403 rate limit exceeded", "rate_limit"),
                 ("HTTP 429", "rate_limit"), ("HTTP 403 forbidden", "permission"),
                 ("HTTP 404", "not_found"), ("HTTP 503", "server"), ("oops", "gh_failure")]
        for output, kind in cases:
            def run(argv, **kwargs):
                raise subprocess.CalledProcessError(1, argv, stderr=output)
            with self.subTest(output=output), self.assertRaises(FindingHandoffError) as error:
                gh.current_login(run)
            self.assertEqual(kind, error.exception.kind)
            self.assertIsInstance(error.exception, KarteUsageError)
            self.assertNotIsInstance(error.exception, KarteNotFound)
        for failure, kind in ((subprocess.TimeoutExpired("gh", 30), "timeout"),
                              (FileNotFoundError(), "gh_missing")):
            with self.subTest(kind=kind), self.assertRaises(FindingHandoffError) as error:
                gh.current_login(lambda *args, **kwargs: (_ for _ in ()).throw(failure))
            self.assertEqual(kind, error.exception.kind)
        for result, kind in ((SimpleNamespace(stdout="HTTP/2 200\n\n{"), "invalid_json"),
                             (reply([]), "response_shape")):
            with self.assertRaises(FindingHandoffError) as error:
                gh.current_login(lambda *args, **kwargs: result)
            self.assertEqual(kind, error.exception.kind)

    def test_issue_identity_and_flags(self):
        for field, value in (("html_url", "https://github.com/x/r/issues/9"),
                             ("repository_url", "https://api.github.com/repos/x/r"), ("number", 10)):
            data = issue() | {field: value}
            with self.subTest(field=field), self.assertRaises(FindingHandoffError) as error:
                gh.get_issue("o/r#9", lambda *args, **kwargs: reply(data))
            self.assertEqual("moved", error.exception.kind)
        data = issue() | {"locked": True, "pull_request": {"url": "x"}}
        self.assertEqual(data, gh.get_issue("O/R#9", lambda *args, **kwargs: reply(data)))

    def test_comment_and_login_calls(self):
        seen = []
        def run(argv, **kwargs):
            seen.append((argv, kwargs))
            return reply({"login": "me"} if argv[-1] == "user" else comment())
        self.assertEqual("me", gh.current_login(run))
        self.assertEqual(comment(), gh.get_comment("o/r#9", 1, run))
        self.assertEqual(comment(), gh.post_comment("o/r#9", "x $(literal)", run))
        self.assertIn("body=x $(literal)", seen[-1][0])
        self.assertTrue(all(kwargs["timeout"] == 30 for _, kwargs in seen))
        other = comment() | {"issue_url": "https://api.github.com/repos/x/r/issues/9"}
        with self.assertRaises(FindingHandoffError) as error:
            gh.get_comment("o/r#9", 1, lambda *args, **kwargs: reply(other))
        self.assertEqual("moved", error.exception.kind)
