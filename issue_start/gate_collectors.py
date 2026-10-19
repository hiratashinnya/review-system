from __future__ import annotations

from typing import Any, Mapping

from blocker_gate.github import GitHubCollector
from .gate_support import IssueStartError



class IssueStartGitHubCollector(GitHubCollector):
    """Read issue title and URL for a fresh blocker denial report."""

    def issue_metadata(self, repository: str, number: int) -> Mapping[str, Any]:
        value, _headers = self._get(f"/repos/{repository}/issues/{number}")
        if not isinstance(value, dict):
            raise IssueStartError("ISSUE_START_REPORT_API_PARTIAL")
        return value


class SnapshotIssueMetadata:
    """Build denial metadata from snapshot values when GitHub is unreachable."""

    def __init__(self, metadata: Mapping[str, Mapping[str, str]]) -> None:
        self._metadata = metadata

    def issue_metadata(self, repository: str, number: int) -> Mapping[str, Any]:
        value = self._metadata.get(f"{repository}#{number}")
        if value is None:
            raise IssueStartError(
                "ISSUE_START_SNAPSHOT_REPORT_MISSING", f"{repository}#{number}"
            )
        return value
