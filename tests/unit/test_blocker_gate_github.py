"""GitHub read-only collector の pagination/error integration fixtures。"""

import json
import unittest

from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot


def response(value, headers=None, status=200):
    return status, headers or {}, json.dumps(value).encode("utf-8")


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.get_calls = []
        self.post_calls = []

    def get(self, url, headers):
        self.get_calls.append((url, dict(headers)))
        return self.responses[url]

    def post(self, url, headers, body):
        self.post_calls.append((url, dict(headers), body))
        return self.responses[(url, body)]


class GitHubCollectorTests(unittest.TestCase):
    def test_rest_relation_pagination_is_completed(self):
        base = "https://api.github.com/repos/example/repo/issues"
        blocker_page_2 = base + "/10/dependencies/blocked_by?per_page=100&page=2"
        transport = FakeTransport(
            {
                base + "/10": response({"number": 10, "node_id": "I10", "state": "open", "state_reason": None, "parent_issue_url": None, "repository_url": "https://api.github.com/repos/example/repo"}),
                base + "/10/dependencies/blocked_by?per_page=100": response([], {"Link": f'<{blocker_page_2}>; rel="next"'}),
                blocker_page_2: response([{"number": 9, "repository_url": "https://api.github.com/repos/example/repo"}]),
                base + "/10/sub_issues?per_page=100": response([]),
                base + "/9": response({"number": 9, "node_id": "I9", "state": "closed", "state_reason": "completed", "parent_issue_url": None, "repository_url": "https://api.github.com/repos/example/repo"}),
                base + "/9/dependencies/blocked_by?per_page=100": response([]),
                base + "/9/sub_issues?per_page=100": response([]),
            }
        )
        snapshot = GitHubCollector("token", transport).collect_issue("example/repo", 10)
        self.assertTrue(snapshot["pages_complete"])
        self.assertEqual(snapshot["nodes"]["example/repo#10"]["blocked_by"], ["example/repo#9"])
        self.assertIn(blocker_page_2, [call[0] for call in transport.get_calls])
        result = evaluate_snapshot(snapshot)
        self.assertEqual(result["result"], "ALLOW")

    def test_permission_and_invalid_json_are_error_not_empty_graph(self):
        url = "https://api.github.com/repos/example/repo/issues/10"
        cases = (
            ((403, {}, b"{}"), "API_PERMISSION"),
            ((200, {}, b"not-json"), "API_PARTIAL_RESPONSE"),
        )
        for raw, reason in cases:
            with self.subTest(reason=reason):
                transport = FakeTransport({url: raw})
                snapshot = GitHubCollector(None, transport).collect_issue("example/repo", 10)
                self.assertIn(reason, snapshot["errors"])
                result = evaluate_snapshot(snapshot)
                self.assertEqual(result["result"], "ERROR")
                self.assertFalse(result["permit_issued"])

    def test_api_version_and_authorization_headers_are_bound(self):
        url = "https://api.github.com/repos/example/repo/issues/10"
        transport = FakeTransport({url: (403, {}, b"{}")})
        GitHubCollector("secret", transport).collect_issue("example/repo", 10)
        headers = transport.get_calls[0][1]
        self.assertEqual(headers["X-GitHub-Api-Version"], "2026-03-10")
        self.assertEqual(headers["Authorization"], "Bearer secret")


if __name__ == "__main__":
    unittest.main()
