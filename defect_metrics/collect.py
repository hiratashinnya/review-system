"""Compatibility exports for issue and pull request collection."""

from .model import IssueRecord, PullRequestRecord, parse_timestamp

import subprocess

from .collect_fetch import (
    DEFAULT_FETCH_LIMIT,
    ISSUE_FIELDS,
    PULL_FIELDS,
    _ensure_not_truncated,
    _run_gh,
)
from .collect_load import CollectionError, _optional_timestamp, load_issues, load_pulls, read_json_file


def fetch_issues(
    repository: str, limit: int = DEFAULT_FETCH_LIMIT
) -> list[IssueRecord]:
    from .collect_fetch import fetch_issues as fetch

    return fetch(repository, limit, runner=_run_gh)


def fetch_pulls(
    repository: str, limit: int = DEFAULT_FETCH_LIMIT
) -> list[PullRequestRecord]:
    from .collect_fetch import fetch_pulls as fetch

    return fetch(repository, limit, runner=_run_gh)


__all__ = [
    "DEFAULT_FETCH_LIMIT",
    "ISSUE_FIELDS",
    "PULL_FIELDS",
    "CollectionError",
    "IssueRecord",
    "PullRequestRecord",
    "fetch_issues",
    "fetch_pulls",
    "load_issues",
    "load_pulls",
    "parse_timestamp",
    "read_json_file",
]
