"""blocker gateのGitHub読み取り処理が使用するHTTP transportとエラー。"""

from __future__ import annotations

from typing import Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .graphql_request import validate_read_request
from .read_request_policy import GRAPHQL_URL, read_headers, validate_rest_get


class GitHubReadError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ReadTransport(Protocol):
    """REST GETと単一GraphQL queryのPOSTのみを許可する読み取り契約。"""

    def get(self, url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str], bytes]: ...
    def post(self, url: str, headers: Mapping[str, str], body: bytes) -> tuple[int, Mapping[str, str], bytes]: ...


class UrlLibReadTransport:
    """REST GETとGraphQL query専用。入力契約違反は送信前にValueErrorにする。"""

    def get(self, url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str], bytes]:
        validate_rest_get(url)
        return self._open(Request(url, headers=read_headers(headers, graphql=False), method="GET"))

    def post(self, url: str, headers: Mapping[str, str], body: bytes) -> tuple[int, Mapping[str, str], bytes]:
        if url != GRAPHQL_URL:
            raise ValueError("POST is permitted only at the GitHub GraphQL endpoint")
        validate_read_request(body)
        request = Request(url, data=body, headers=read_headers(headers, graphql=True), method="POST")
        return self._open(request)

    @staticmethod
    def _open(request: Request) -> tuple[int, Mapping[str, str], bytes]:
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub URLs
                return response.status, dict(response.headers.items()), response.read()
        except HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()
        except (TimeoutError, URLError) as exc:
            # Issue #345［B］: HTTP 応答すら得られていない（DNS/接続/tunnel/timeout）。
            # GitHub が下した判断ではないので「到達不能」として分類する。
            raise GitHubReadError("API_UNREACHABLE") from exc
