"""Immutable branch source result and GitHub API contract."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

POLICY_VERSION = "branch-source/1.0"

@dataclass(frozen=True)
class BranchSourceResult:
    repository: str
    default_branch: str
    source_oid: str
    source_kind: str
    base_pr: int | None
    policy_version: str = POLICY_VERSION


class BranchApi(Protocol):
    def repository(self, repository: str) -> Mapping[str, Any]: ...

    def pull_request(self, repository: str, number: int) -> Mapping[str, Any]: ...
