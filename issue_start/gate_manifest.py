from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .gate_support import (
    ENTRYPOINT_MANIFEST, ISSUE_START_POLICY_VERSION, MANIFEST_SCHEMA_VERSION,
    IssueStartError, IssueStartRequest, IsolationOnlyAck, _BRANCH, _OID, _REPOSITORY, _REF,
    _HANDOFF_PATH,
)



def _manifest() -> Mapping[str, Any]:
    try:
        raw = json.loads(ENTRYPOINT_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IssueStartError("ISSUE_START_MANIFEST_ERROR") from exc
    if (
        not isinstance(raw, dict)
        or raw.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or raw.get("policy_version") != ISSUE_START_POLICY_VERSION
    ):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return raw


def _entries(key: str, *, required: bool) -> list[Mapping[str, Any]]:
    value = _manifest().get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value) or not all(
        isinstance(item, dict) for item in value
    ):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return value


def _managed_entries() -> list[Mapping[str, Any]]:
    return _entries("managed", required=True)


def _isolation_only_entries() -> list[Mapping[str, Any]]:
    """`isolation_only` 区分のエントリ（未宣言の manifest では空）。"""
    return _entries("isolation_only", required=False)


def _agent_types(entries: Sequence[Mapping[str, Any]]) -> set[str]:
    raw = [item.get("agent_type") for item in entries]
    if not all(isinstance(value, str) and value for value in raw):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return set(raw)


def _request(raw: Mapping[str, Any]) -> IssueStartRequest:
    expected = {"entrypoint", "repository", "issue"}
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    entrypoint = raw.get("entrypoint")
    repository = raw.get("repository")
    issue = raw.get("issue")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN")
    if entrypoint not in {item.get("entrypoint") for item in _managed_entries()}:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", entrypoint)
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise IssueStartError("ISSUE_START_REPOSITORY_INVALID")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise IssueStartError("ISSUE_START_ISSUE_INVALID")
    return IssueStartRequest(entrypoint, repository, issue)


def _claude_request(raw: Mapping[str, Any]) -> IssueStartRequest:
    """Claude の既存 V1 marker schema を変えず、blocker binding だけを返す。"""
    expected = {
        "entrypoint", "repository", "issue", "branch_name", "base_ref", "base_oid", "base_pr"
    }
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    branch_name = raw.get("branch_name")
    base_ref = raw.get("base_ref")
    base_oid = raw.get("base_oid")
    base_pr = raw.get("base_pr")
    if not isinstance(branch_name, str) or not _BRANCH.fullmatch(branch_name):
        raise IssueStartError("ISSUE_START_BRANCH_INVALID")
    if not isinstance(base_ref, str) or not _REF.fullmatch(base_ref):
        raise IssueStartError("ISSUE_START_BASE_REF_INVALID")
    if not isinstance(base_oid, str) or not _OID.fullmatch(base_oid):
        raise IssueStartError("ISSUE_START_BASE_OID_INVALID")
    if base_pr is not None and (
        not isinstance(base_pr, int) or isinstance(base_pr, bool) or base_pr < 1
    ):
        raise IssueStartError("ISSUE_START_BASE_PR_INVALID")
    return _request({key: raw[key] for key in ("entrypoint", "repository", "issue")})
