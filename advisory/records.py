"""Advisory schema and references validator."""

import re
from datetime import date, datetime

from .audit import validate_events
from .identity import identifier
from .record_fields import FIELDS, STATES

SOURCE = re.compile(r"(?:issue|pr):(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#)?[1-9]\d*\Z|finding:F-\d+-\d+\Z")
ISSUE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9]\d*\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
VERSION = re.compile(r"[0-9]+\.[0-9]+\Z")


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_record(record: object) -> list[str]:
    if not isinstance(record, dict) or set(record) != set(FIELDS):
        return ["record field set mismatch"]
    errors = []
    if record["schema_version"] != "advisory/v1":
        errors.append("unsupported schema_version")
    try:
        if record["id"] != identifier(record["topic"], record["created_on"]):
            errors.append("immutable id/topic/date mismatch")
    except (TypeError, ValueError) as exc:
        errors.append(f"invalid identity: {exc}")
    if record["status"] not in STATES or type(record["revision"]) is not int:
        errors.append("invalid state/revision")
    if not isinstance(record["base_sha256"], str) or (record["base_sha256"]
            and not DIGEST.fullmatch(record["base_sha256"])):
        errors.append("invalid base_sha256")
    for name in ("evidence", "recommendation", "triage_rationale", "policy_version"):
        if not _text(record[name]):
            errors.append("missing " + name)
    if not isinstance(record["policy_version"], str) or not VERSION.fullmatch(record["policy_version"]):
        errors.append("invalid policy_version")
    for name in ("sources", "related_ids"):
        value = record[name]
        if not isinstance(value, list) or (name == "sources" and not value):
            errors.append("invalid " + name)
        elif any(not isinstance(item, str) or not item for item in value) or len(set(value)) != len(value):
            errors.append("invalid or repeated " + name)
        elif name == "sources" and any(not SOURCE.fullmatch(item) for item in value):
            errors.append("invalid source reference")
    if not isinstance(record["duplicate_reason"], str):
        errors.append("invalid duplicate_reason")
    if not isinstance(record["promoted_issue"], str) or (
            record["promoted_issue"] and not ISSUE.fullmatch(record["promoted_issue"])):
        errors.append("invalid promoted_issue")
    if record["status"] == "promoted" and not record["promoted_issue"]:
        errors.append("promoted status must have an existing issue")
    if record["promoted_issue"] and not any(
        isinstance(event, dict) and event.get("action") == "promote"
        for event in record["history"] if isinstance(record["history"], list)
    ):
        errors.append("promoted issue must have an audit promotion event")
    if isinstance(record["related_ids"], list) and record["id"] in record["related_ids"]:
        errors.append("self-referential related_ids")
    errors.extend(validate_events(record))
    return errors
