"""blocker gate の閉じた型と canonicalization helper。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping

POLICY_VERSION = "1.0"
CLASSIFIER_VERSION = "1.0"
RESULT_SCHEMA = "blocker-gate-result/v1"
SNAPSHOT_SCHEMA = "blocker-gate-snapshot/v1"


class IssueClass(str, Enum):
    OPEN = "OPEN"
    CLOSED_COMPLETED = "CLOSED_COMPLETED"
    CLOSED_NOT_PLANNED = "CLOSED_NOT_PLANNED"
    UNKNOWN = "UNKNOWN"


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ERROR = "ERROR"


ALLOW_REASONS = frozenset({"NO_VIOLATION", "NO_CLOSING_EFFECT", "WAIVER_APPLIED"})
BLOCK_REASONS = frozenset(
    {
        "OPEN_BLOCKER",
        "CLOSURE_OPEN_DESCENDANT",
        "TARGET_ISSUE_NOT_OPEN",
        "PR_NOT_OPEN",
        "PR_DRAFT",
        "AUTO_MERGE_DENIED",
    }
)
ERROR_REASONS = frozenset(
    {
        "CLASSIFIER_UNKNOWN",
        "TARGET_AMBIGUOUS",
        "MODE_MISMATCH",
        "API_UNAVAILABLE",
        "API_PERMISSION",
        # Issue #345［B］: GitHub まで届かなかった（手前の proxy/network が
        # 遮断した）ことを、権限拒否 API_PERMISSION から分離する。
        "API_UNREACHABLE",
        "API_PARTIAL_RESPONSE",
        "PAGINATION_INCOMPLETE",
        "GRAPH_LIMIT_EXCEEDED",
        "GRAPH_CYCLE",
        "IDENTITY_MISMATCH",
        "ISSUE_STATE_UNKNOWN",
        "RELATION_INCONSISTENT",
        "RELATION_TARGET_UNREADABLE",
        "CROSS_REPOSITORY_UNSUPPORTED",
        "MERGE_METHOD_UNKNOWN",
        "MERGE_SETTINGS_AMBIGUOUS",
        "MERGE_OVERRIDE_AMBIGUOUS",
        "MERGE_MESSAGE_AMBIGUOUS",
        "REBASE_MESSAGE_AMBIGUOUS",
        "MESSAGE_SOURCE_INCOMPLETE",
        "CLOSING_KEYWORD_PARSE",
        "WAIVER_SCHEMA_INVALID",
        "WAIVER_INVALID",
        "REEVALUATION_LIMIT",
        "RESULT_CONTRACT_INVALID",
        "HOOK_INTEGRITY_ERROR",
        "INTERNAL_ERROR",
    }
)
INCOMPLETE_REASONS = frozenset(
    {
        "API_UNAVAILABLE",
        "API_PERMISSION",
        "API_UNREACHABLE",
        "API_PARTIAL_RESPONSE",
        "PAGINATION_INCOMPLETE",
        "RELATION_TARGET_UNREADABLE",
        "MESSAGE_SOURCE_INCOMPLETE",
    }
)


@dataclass(frozen=True)
class IssueNode:
    ref: str
    node_id: str
    state: IssueClass
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    children: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, ref: str, raw: Mapping[str, Any]) -> "IssueNode":
        expected = {"node_id", "state", "blocked_by", "parent", "children"}
        if set(raw) != expected:
            raise ValueError(f"node {ref}: keys mismatch")
        return cls(
            ref=ref,
            node_id=_required_string(raw["node_id"], "node_id"),
            state=IssueClass(raw["state"]),
            blocked_by=tuple(_string_list(raw["blocked_by"], "blocked_by")),
            parent=_optional_string(raw["parent"], "parent"),
            children=tuple(_string_list(raw["children"], "children")),
        )


@dataclass(frozen=True)
class Finding:
    code: str
    subject: str
    path: tuple[str, ...]
    fingerprint: str = ""
    waiver_id: str | None = None
    waiver_evidence: Mapping[str, str] | None = None

    def finalized(self, mode: str) -> "Finding":
        digest = finding_fingerprint(self.code, mode, self.subject, self.path)
        return Finding(
            self.code,
            self.subject,
            self.path,
            digest,
            self.waiver_id,
            self.waiver_evidence,
        )

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "subject": self.subject,
            "path": list(self.path),
            "fingerprint": self.fingerprint,
            "waiver_id": self.waiver_id,
        }
        if self.waiver_evidence is not None:
            value["waiver_evidence"] = dict(self.waiver_evidence)
        return value


@dataclass(frozen=True)
class Snapshot:
    mode: str
    repository: str
    subject_type: str
    subject_number: int
    roots: tuple[str, ...]
    virtual_closed: frozenset[str]
    nodes: Mapping[str, IssueNode]
    pages_complete: bool
    errors: tuple[str, ...]
    fetched_at: str
    graphql_closing_set: tuple[str, ...] = ()
    delivered_message_closing_set: tuple[str, ...] = ()
    binding: Mapping[str, Any] = field(default_factory=dict)


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be non-empty string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, label)


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be string array")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must be unique")
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def finding_fingerprint(code: str, mode: str, subject: str, path: Iterable[str]) -> str:
    return fingerprint({"code": code, "mode": mode, "path": list(path), "subject": subject})


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda item: (item.code, item.subject, item.path))
