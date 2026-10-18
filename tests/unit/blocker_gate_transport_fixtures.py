"""読み取りtransportの送信境界とcollectorの既存query互換性を検証する。"""

import json
import unittest
from unittest.mock import patch

from blocker_gate.transport import UrlLibReadTransport


GRAPHQL = "https://api.github.com/graphql"
REST = "https://api.github.com/repos/example/repo"


class FakeResponse:
    status = 200
    headers = {"X-Test": "ok"}

    def __init__(self, data=b"response"):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.data


def body(query="query { viewer { login } }", **extra):
    return json.dumps({"query": query, **extra}).encode()


class ReadTransportCase(unittest.TestCase):
    def setUp(self):
        self.transport = UrlLibReadTransport()


    def assert_rejected(self, *, payload=None, url=GRAPHQL, headers=None, method="post"):
        with patch("blocker_gate.transport.urlopen") as opener:
            with self.assertRaises(ValueError):
                if method == "post":
                    self.transport.post(url, headers or {}, body() if payload is None else payload)
                else:
                    self.transport.get(url, headers or {})
            opener.assert_not_called()
