"""GitHub API transportの名前と説明が公開するHTTP機能に一致することを検証する。"""

from unittest.mock import patch
import unittest

from blocker_gate import github
from blocker_gate.transport import GitHubApiTransport, UrlLibGitHubApiTransport


class FakeResponse:
    status = 200
    headers = {"X-Test": "ok"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return b"response"


class GitHubApiTransportTests(unittest.TestCase):
    def test_transport_contract_names_and_documents_post_capability(self):
        self.assertIs(github.GitHubApiTransport, GitHubApiTransport)
        self.assertIs(github.UrlLibGitHubApiTransport, UrlLibGitHubApiTransport)
        self.assertIn("POST", UrlLibGitHubApiTransport.__doc__)
        self.assertIn("GitHubの状態を変更できる", UrlLibGitHubApiTransport.__doc__)

    def test_urllib_transport_sends_get_and_post_requests(self):
        requests = []

        def open_request(request, *, timeout):
            requests.append((request, timeout))
            return FakeResponse()

        transport = UrlLibGitHubApiTransport()
        with patch("blocker_gate.transport.urlopen", side_effect=open_request):
            self.assertEqual(
                transport.get("https://api.github.com/repos/example/repo", {"Accept": "json"}),
                (200, {"X-Test": "ok"}, b"response"),
            )
            self.assertEqual(
                transport.post("https://api.github.com/graphql", {"Accept": "json"}, b"query"),
                (200, {"X-Test": "ok"}, b"response"),
            )

        self.assertEqual([request.get_method() for request, _ in requests], ["GET", "POST"])
        self.assertEqual([request.data for request, _ in requests], [None, b"query"])
        self.assertEqual([timeout for _, timeout in requests], [30, 30])


if __name__ == "__main__":
    unittest.main()
