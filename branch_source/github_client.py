"""Read-only GitHub API client with fail-close error classification."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from typing import Any, Mapping
from blocker_gate.auth import github_api_failure_reason
from .validation import BranchSourceError

API_VERSION = "2022-11-28"

class GitHubBranchClient:
    """GitHub standard REST API の read-only client（外部 SaaS 不使用）。"""

    def __init__(self, token: str | None = None) -> None:
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "review-system-branch-source/1.0",
        }
        if token:
            self._headers["Authorization"] = "Bearer " + token

    def _get(self, path: str) -> Mapping[str, Any]:
        request = urllib.request.Request(
            "https://api.github.com" + path,
            headers=self._headers,
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            common_failure = github_api_failure_reason(exc.code, exc.headers or {})
            if common_failure is not None:
                raise BranchSourceError(common_failure) from None
            if exc.code == 404:
                raise BranchSourceError("BRANCH_API_PERMISSION_OR_NOT_FOUND") from None
            raise BranchSourceError("API_UNAVAILABLE") from None
        except (urllib.error.URLError, TimeoutError):
            # Issue #345 F-345-07: HTTP 応答すら得られていない（DNS/接続/tunnel/
            # timeout）。GitHub が下した判断ではないので「到達不能」に分類する。
            # `github_api_failure_reason` 経由の provenance 欠落 401/403 が
            raise BranchSourceError("API_UNREACHABLE") from None
        except OSError:
            raise BranchSourceError("API_UNAVAILABLE") from None
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BranchSourceError("API_PARTIAL_RESPONSE") from None
        if not isinstance(value, dict):
            raise BranchSourceError("API_PARTIAL_RESPONSE")
        return value

    def repository(self, repository: str) -> Mapping[str, Any]:
        return self._get(f"/repos/{repository}")

    def pull_request(self, repository: str, number: int) -> Mapping[str, Any]:
        return self._get(f"/repos/{repository}/pulls/{number}")
