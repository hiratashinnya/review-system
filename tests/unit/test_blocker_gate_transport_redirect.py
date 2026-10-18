"""標準urllib redirect経路で全hopの読み取り送信境界を検証する。"""

from unittest.mock import patch
from urllib.request import build_opener

from tests.unit.blocker_gate_redirect_fixtures import MemoryNetwork
from tests.unit.blocker_gate_transport_fixtures import GRAPHQL, REST, ReadTransportCase, body


class ReadRedirectTests(ReadTransportCase):
    def send(self, method, redirects):
        network = MemoryNetwork(redirects)
        def local_opener(handler):
            return build_opener(handler, network)
        with patch("blocker_gate.read_redirect.build_opener", side_effect=local_opener):
            headers = {"Authorization": "Bearer TEST_TOKEN"}
            result = (self.transport.get(REST, headers) if method == "get"
                      else self.transport.post(GRAPHQL, headers, body()))
        return result, network.seen

    def test_unsafe_redirect_never_sends_second_request(self):
        targets = ["https://outside.example/repos/a/b", "http://api.github.com/repos/a/b",
                   "http://outside.example/collect", GRAPHQL, REST + "/../../graphql",
                   "https://[invalid/repos/a/b", "ftp://api.github.com/repos/a/b"]
        for method in ["get", "post"]:
            for code in [301, 302, 303, 307, 308]:
                for target in targets:
                    with self.subTest(method=method, code=code, target=target):
                        result, seen = self.send(method, [(code, target)])
                        self.assertEqual(result[0], code)
                        self.assertEqual(len(seen), 1)

    def test_safe_repository_redirect_retains_authorization(self):
        for method in ["get", "post"]:
            for code in [301, 302, 303]:
                with self.subTest(method=method, code=code):
                    result, seen = self.send(method, [(code, REST + "/issues?page=2")])
                    self.assertEqual(result[0], 200)
                    self.assertEqual(seen[1], (REST + "/issues?page=2", "GET", "Bearer TEST_TOKEN"))
        for code in [307, 308]:
            self.assertEqual(self.send("get", [(code, REST + "/issues")])[0][0], 200)
            result, seen = self.send("post", [(code, REST + "/issues")])
            self.assertEqual(result[0], code)
            self.assertEqual(len(seen), 1)

    def test_redirect_chain_checks_every_hop(self):
        for method in ["get", "post"]:
            for target in ["https://outside.example/repos/a/b", "http://api.github.com/repos/a/b", GRAPHQL]:
                with self.subTest(method=method, target=target):
                    result, seen = self.send(method, [(302, REST + "/issues"), (303, target)])
                    self.assertEqual(result[0], 303)
                    self.assertEqual(len(seen), 2)
                    self.assertTrue(all(url.startswith(REST) or url == GRAPHQL for url, _, _ in seen))

    def test_relative_and_safe_redirect_chain_reaches_final_response(self):
        for method in ["get", "post"]:
            result, seen = self.send(method, [(302, REST + "/issues"), (303, "issues?page=2")])
            self.assertEqual(result[0], 200)
            self.assertEqual(len(seen), 3)
            self.assertEqual(seen[-1], (REST + "/issues?page=2", "GET", "Bearer TEST_TOKEN"))
