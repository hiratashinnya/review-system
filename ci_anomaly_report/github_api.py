"""Read-only GitHub REST transport used by the CI anomaly collector."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


class GitHubAPI:
    """Thin wrapper for the read-only endpoints required by this collector."""

    def __init__(self, token: str, *, api_url: str = "https://api.github.com"):
        self.token = token
        self.api_url = api_url.rstrip("/")

    def get(self, path_or_url: str, params: dict[str, object] | None = None) -> Any:
        url = path_or_url if path_or_url.startswith("http") else self.api_url + path_or_url
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "review-system-ci-anomaly-report",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
