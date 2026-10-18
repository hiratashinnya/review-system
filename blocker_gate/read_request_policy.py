"""GitHub読み取りtransportのURLとHTTPヘッダの許可境界。"""

from typing import Mapping
from urllib.parse import unquote, urlsplit


GRAPHQL_URL = "https://api.github.com/graphql"
_HEADERS = frozenset({"accept", "authorization", "user-agent", "x-github-api-version", "content-type"})


def read_headers(headers: Mapping[str, str], *, graphql: bool) -> dict[str, str]:
    """既存collectorのヘッダだけを許可し、JSONの解釈とHTTP framingを固定する。"""
    result: dict[str, str] = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise ValueError("HTTP header names and values must be strings")
        key = name.lower()
        if key not in _HEADERS or key in result or any(char in name + value for char in "\r\n"):
            raise ValueError("Unsupported or duplicate HTTP header")
        result[key] = value
    if graphql:
        result["content-type"] = "application/json"
    return result


def validate_rest_get(url: str) -> None:
    """固定GitHub originの/repos/配下のみ許可し、path正規化による脱出を拒否する。"""
    if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise ValueError("Invalid GitHub REST URL")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "api.github.com"
            or not parsed.path.startswith("/repos/") or parsed.fragment):
        raise ValueError("Only GitHub repository REST GET requests are permitted")
    path = parsed.path
    for _ in range(len(path) + 1):
        if "\\" in path or any(part in {".", ".."} for part in path.split("/")):
            raise ValueError("Path traversal is forbidden")
        decoded = unquote(path, errors="strict")
        if decoded == path:
            return
        path = decoded
    raise ValueError("Invalid encoded REST path")
