"""機械可読 waiver の strict parser と read-only verifier。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping

from .model import POLICY_VERSION

_WAIVER_ID = re.compile(r"^BW-[0-9]{8}-[0-9]{3,}$")
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REPOSITORY = re.compile(r"^[^/\s]+/[^/\s]+$")
_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class WaiverError(ValueError):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class WaiverContext:
    repository: str
    mode: str
    subject_type: str
    subject_number: int
    finding_fingerprint: str
    now: datetime


@dataclass(frozen=True)
class WaiverEvidence:
    default_branch: str
    default_head: str
    policy_blob_sha: str
    waiver_blob_sha: str
    approval_commit: str
    commit_is_default_head_ancestor: bool
    signature_verified: bool
    signer_login: str | None
    ruleset_active: bool
    history_bypass_free: bool
    deletion_protected: bool
    non_fast_forward_protected: bool


@dataclass(frozen=True)
class WaiverMaterial:
    """default branch head から read-only 収集した未解釈のwaiver材料。"""

    policy_bytes: bytes
    waiver_bytes: bytes
    evidence: WaiverEvidence


@dataclass(frozen=True)
class WaiverCollection:
    """waiver候補と、候補取得中に生じたfail-close error。"""

    materials: tuple[WaiverMaterial, ...] = ()
    errors: tuple[str, ...] = ()


def _valid_branch_name(value: Any) -> bool:
    """git-check-ref-format相当の禁止形を副作用なしで閉じて検査する。"""
    if type(value) is not str or not 1 <= len(value) <= 255:
        return False
    if value == "@" or value.startswith("-") or value.startswith("/") or value.endswith(("/", ".")):
        return False
    if ".." in value or "@{" in value or "//" in value:
        return False
    if any(ord(char) <= 32 or ord(char) == 127 or char in "~^:?*[\\\\" for char in value):
        return False
    return all(part and not part.startswith(".") and not part.endswith(".lock") for part in value.split("/"))


def _decode(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "non-UTF-8") from exc
    if "\x00" in text or text.startswith("---") or "\n---" in text or "\n..." in text:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "multiple document or NUL")
    return text


def _scalar(raw: str) -> str | int | bool | None:
    value = raw.strip()
    if not value:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "empty scalar")
    if value[0:1] in {"&", "*", "!", "{", "[", ">", "|"}:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "YAML extension denied")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    if value == "null":
        return None
    if re.fullmatch(r"0|[1-9][0-9]*", value):
        return int(value)
    return value


def _strict_yaml(data: bytes) -> dict[str, Any]:
    text = _decode(data)
    lines: list[tuple[int, int, str]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise WaiverError("WAIVER_SCHEMA_INVALID", f"line {line_number}: tab")
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if indent % 2:
            raise WaiverError("WAIVER_SCHEMA_INVALID", f"line {line_number}: indentation")
        lines.append((line_number, indent, stripped))

    def mapping(index: int, indent: int) -> tuple[dict[str, Any], int]:
        value: dict[str, Any] = {}
        while index < len(lines):
            line_number, current, body = lines[index]
            if current < indent:
                break
            if current != indent or body.startswith("- "):
                raise WaiverError("WAIVER_SCHEMA_INVALID", f"line {line_number}: structure")
            key, separator, rest = body.partition(":")
            if not separator or not re.fullmatch(r"[a-z_]+", key):
                raise WaiverError("WAIVER_SCHEMA_INVALID", f"line {line_number}: key")
            if key in value:
                raise WaiverError("WAIVER_SCHEMA_INVALID", f"line {line_number}: duplicate {key}")
            rest = rest.strip()
            index += 1
            if rest:
                value[key] = _scalar(rest)
                continue
            if index >= len(lines) or lines[index][1] <= indent:
                raise WaiverError("WAIVER_SCHEMA_INVALID", f"line {line_number}: empty mapping")
            next_body = lines[index][2]
            if next_body.startswith("- "):
                items: list[Any] = []
                while index < len(lines) and lines[index][1] == indent + 2 and lines[index][2].startswith("- "):
                    item_line, _, item_body = lines[index]
                    raw_item = item_body[2:].strip()
                    if not raw_item:
                        raise WaiverError("WAIVER_SCHEMA_INVALID", f"line {item_line}: empty item")
                    items.append(_scalar(raw_item))
                    index += 1
                value[key] = items
            else:
                value[key], index = mapping(index, indent + 2)
        return value, index

    result, end = mapping(0, 0)
    if end != len(lines):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "trailing structure")
    return result


def _keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise WaiverError("WAIVER_SCHEMA_INVALID", f"{label} keys mismatch")


def _utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise WaiverError("WAIVER_SCHEMA_INVALID", f"{label} must use UTC Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise WaiverError("WAIVER_SCHEMA_INVALID", f"{label} invalid") from exc


def parse_policy_yaml(data: bytes) -> dict[str, Any]:
    value = _strict_yaml(data)
    _keys(
        value,
        {"schema", "policy_version", "approver_allowlist", "max_waiver_lifetime_hours", "protected_default_branch"},
        "policy",
    )
    if value["schema"] != "blocker-gate-policy/v1" or value["policy_version"] != POLICY_VERSION:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "policy version")
    allowlist = value["approver_allowlist"]
    if not isinstance(allowlist, list) or not allowlist or len(allowlist) != len(set(allowlist)):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "approver allowlist")
    if any(not isinstance(login, str) or not _LOGIN.fullmatch(login) for login in allowlist):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "approver login")
    lifetime = value["max_waiver_lifetime_hours"]
    if type(lifetime) is not int or lifetime < 1 or lifetime > 168:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "max lifetime")
    if not _valid_branch_name(value["protected_default_branch"]):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "protected branch")
    return value


def parse_waiver_yaml(data: bytes) -> dict[str, Any]:
    value = _strict_yaml(data)
    _keys(
        value,
        {
            "schema", "id", "policy_version", "repository", "owner", "reason",
            "requested_by", "approved_by", "approved_at", "expires_at", "scope",
        },
        "waiver",
    )
    if value["schema"] != "blocker-gate-waiver/v1" or value["policy_version"] != POLICY_VERSION:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "waiver version")
    if not isinstance(value["id"], str) or not _WAIVER_ID.fullmatch(value["id"]):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "waiver id")
    if not isinstance(value["repository"], str) or not _REPOSITORY.fullmatch(value["repository"]):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "repository")
    for label in ("owner", "requested_by", "approved_by"):
        if not isinstance(value[label], str) or not _LOGIN.fullmatch(value[label]):
            raise WaiverError("WAIVER_SCHEMA_INVALID", label)
    reason = value["reason"]
    if not isinstance(reason, str) or not 1 <= len(reason) <= 1000 or _CONTROL.search(reason):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "reason")
    approved = _utc(value["approved_at"], "approved_at")
    expires = _utc(value["expires_at"], "expires_at")
    if expires <= approved:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "expiry order")
    scope = value["scope"]
    if not isinstance(scope, dict):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "scope")
    _keys(scope, {"mode", "subject", "finding_fingerprints"}, "scope")
    if scope["mode"] not in {"issue-start", "pr-merge"}:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "scope mode")
    subject = scope["subject"]
    if not isinstance(subject, dict):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "scope subject")
    _keys(subject, {"type", "number"}, "scope subject")
    expected_type = "issue" if scope["mode"] == "issue-start" else "pull_request"
    if subject["type"] != expected_type or type(subject["number"]) is not int or subject["number"] < 1:
        raise WaiverError("WAIVER_SCHEMA_INVALID", "scope subject")
    fps = scope["finding_fingerprints"]
    if not isinstance(fps, list) or not fps or len(fps) != len(set(fps)):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "finding fingerprints")
    if any(not isinstance(item, str) or not _FINGERPRINT.fullmatch(item) for item in fps):
        raise WaiverError("WAIVER_SCHEMA_INVALID", "finding fingerprint")
    return value


def verify_waiver(
    waiver: Mapping[str, Any],
    policy: Mapping[str, Any],
    context: WaiverContext,
    evidence: WaiverEvidence,
) -> dict[str, str]:
    """既読のwaiver/policy/evidenceだけを検証する。外部・filesystem書込みは行わない。"""
    if type(evidence) is not WaiverEvidence:
        raise WaiverError("WAIVER_INVALID", "evidence type")
    try:
        if (
            not _valid_branch_name(evidence.default_branch)
            or type(evidence.default_head) is not str
            or not _GIT_OID.fullmatch(evidence.default_head)
            or type(evidence.policy_blob_sha) is not str
            or not _FINGERPRINT.fullmatch(evidence.policy_blob_sha)
            or type(evidence.waiver_blob_sha) is not str
            or not _FINGERPRINT.fullmatch(evidence.waiver_blob_sha)
            or type(evidence.approval_commit) is not str
            or not _GIT_OID.fullmatch(evidence.approval_commit)
            or type(evidence.signer_login) is not str
            or not _LOGIN.fullmatch(evidence.signer_login)
        ):
            raise WaiverError("WAIVER_INVALID", "evidence scalar")
        for label in (
            "commit_is_default_head_ancestor",
            "signature_verified",
            "ruleset_active",
            "history_bypass_free",
            "deletion_protected",
            "non_fast_forward_protected",
        ):
            if getattr(evidence, label) is not True:
                raise WaiverError("WAIVER_INVALID", f"{label} is not exact true")
    except AttributeError as exc:
        raise WaiverError("WAIVER_INVALID", "evidence field missing") from exc
    try:
        approved = _utc(waiver["approved_at"], "approved_at")
        expires = _utc(waiver["expires_at"], "expires_at")
        scope = waiver["scope"]
    except (KeyError, TypeError) as exc:
        raise WaiverError("WAIVER_INVALID", "unparsed waiver") from exc
    now = context.now.astimezone(timezone.utc)
    max_seconds = int(policy["max_waiver_lifetime_hours"]) * 3600
    checks = (
        waiver["policy_version"] == policy["policy_version"] == POLICY_VERSION,
        evidence.default_branch == policy["protected_default_branch"],
        waiver["repository"] == context.repository,
        scope["mode"] == context.mode,
        scope["subject"]["type"] == context.subject_type,
        scope["subject"]["number"] == context.subject_number,
        context.finding_fingerprint in scope["finding_fingerprints"],
        waiver["approved_by"] in policy["approver_allowlist"],
        approved <= now < expires,
        0 < (expires - approved).total_seconds() <= max_seconds,
        evidence.signer_login == waiver["approved_by"],
    )
    if not all(checks):
        raise WaiverError("WAIVER_INVALID", "scope, expiry, signer, or ruleset mismatch")
    return {
        "waiver_id": str(waiver["id"]),
        "policy_blob_sha": evidence.policy_blob_sha,
        "waiver_blob_sha": evidence.waiver_blob_sha,
        "approval_commit": evidence.approval_commit,
        "expires_at": str(waiver["expires_at"]),
    }
