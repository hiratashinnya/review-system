"""Shared Issue-start dispatch contract and policy constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

ISSUE_START_POLICY_VERSION = "issue-start/1.0"
BINDING_MARKER = "ISSUE_START_BINDING_V1="
FIX_BINDING_MARKER = "ISSUE_FIX_BINDING_V1="
MANIFEST_SCHEMA_VERSION = "managed-issue-entrypoints/2"
ENTRYPOINT_MANIFEST = Path(__file__).with_name("managed-entrypoints-v2.json")
SNAPSHOT_BRANCH = "blocker-snapshot"
SNAPSHOT_PATH = "snapshot.json"
SNAPSHOT_REMOTE_REF = "refs/remotes/origin/" + SNAPSHOT_BRANCH
SNAPSHOT_MAX_AGE_SECONDS = 600
SNAPSHOT_GIT_TIMEOUT_SECONDS = 30.0
SNAPSHOT_FALLBACK_REASON = "API_UNREACHABLE"
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_BRANCH = _REF
_HANDOFF_PATH = re.compile(r"^tmp/_handoff/(?P<name>[A-Za-z0-9._-]+)\.yaml$")
_HTTPS_REMOTE = re.compile(
    r"^https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/"
    r"([A-Za-z0-9_.-]{1,100}?)(?:\.git)?$"
)
_SSH_REMOTE = re.compile(
    r"^(?:git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100}?)(?:\.git)?$"
)


class IssueStartError(Exception):
    """Fail-closed identity, contract, or API error."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class IssueStartRequest:
    entrypoint: str
    repository: str
    issue: int


@dataclass(frozen=True)
class IsolationOnlyAck:
    """Accepted dispatch binding for the isolation-only fixer path."""

    entrypoint: str
    agent_type: str
    issue: int | None
    round: int | None
    branch_name: str | None
    handoff_path: str | None
    expected_oid: str | None
    repository: str | None
