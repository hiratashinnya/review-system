"""読み取りtransportのHTTP送信境界。"""

from urllib.error import URLError
from unittest.mock import patch

from blocker_gate import github
from tests.unit.blocker_gate_transport_fixtures import GRAPHQL, REST, FakeResponse, ReadTransportCase, body
from blocker_gate.transport import GitHubReadError, ReadTransport, UrlLibReadTransport


class ReadTransportTests(ReadTransportCase):
    def test_public_contract_and_normal_requests(self):
        self.assertIs(github.ReadTransport, ReadTransport)
        self.assertIs(github.UrlLibReadTransport, UrlLibReadTransport)
        with patch("blocker_gate.transport.urlopen", return_value=FakeResponse()) as opener:
            self.assertEqual(self.transport.get(REST, {}), (200, {"X-Test": "ok"}, b"response"))
            self.transport.post(GRAPHQL, {"Content-Type": "text/plain"}, body())
        requests = [call.args[0] for call in opener.call_args_list]
        self.assertEqual([request.get_method() for request in requests], ["GET", "POST"])
        self.assertEqual(requests[1].get_header("Content-type"), "application/json")
        self.assertTrue(all(call.kwargs == {"timeout": 30} for call in opener.call_args_list))


    def test_post_is_bound_to_exact_graphql_endpoint(self):
        for url in [REST + "/issues", GRAPHQL + "?x=1", GRAPHQL + "/", GRAPHQL + "#x",
                    "http://api.github.com/graphql", "https://evil.example/graphql",
                    "https://api.github.com:443/graphql", "https://api.github.com./graphql"]:
            with self.subTest(url=url):
                self.assert_rejected(url=url)


    def test_headers_cannot_change_request_interpretation(self):
        for headers in [{"Host": "evil.example"}, {"Content-Encoding": "gzip"},
                        {"Content-Length": "0"}, {"Transfer-Encoding": "chunked"},
                        {"Accept": "json", "accept": "text"},
                        {"Authorization": "Bearer x\r\nHost: evil.example"},
                        {"Accept\n": "json"}, {"X-HTTP-Method-Override": "DELETE"},
                        {"Accept": 1}]:
            for method, url in [("get", REST), ("post", GRAPHQL)]:
                with self.subTest(headers=headers, method=method):
                    self.assert_rejected(headers=headers, method=method, url=url)


    def test_rest_origin_and_paths_cannot_escape(self):
        for url in [GRAPHQL, "http://api.github.com/repos/a/b", "https://evil.example/repos/a/b",
                    "https://api.github.com@evil.example/repos/a/b", REST + "/../../graphql",
                    REST + "/%2e%2e/%2e%2e/graphql", REST + "/x%2f..%2f..%2fgraphql",
                    REST + "/%252e%252e/graphql", REST + "/x%5c..%5cgraphql",
                    "https://api.github.com/repos/../graphql", REST + "#fragment", REST + "\n"]:
            with self.subTest(url=url):
                self.assert_rejected(url=url, method="get")


    def test_encoded_branch_and_pagination_queries_are_preserved(self):
        urls = [REST + "/git/ref/heads/feature%2Ftopic", REST + "/issues?page=2&per_page=100"]
        with patch("blocker_gate.transport.urlopen", return_value=FakeResponse()) as opener:
            for url in urls:
                self.transport.get(url, {"aCcEpT": "application/json"})
        self.assertEqual([call.args[0].full_url for call in opener.call_args_list], urls)


    def test_network_errors_keep_existing_reason(self):
        with patch("blocker_gate.transport.urlopen", side_effect=URLError("offline")):
            with self.assertRaises(GitHubReadError) as error:
                self.transport.post(GRAPHQL, {}, body())
        self.assertEqual(error.exception.reason, "API_UNREACHABLE")
