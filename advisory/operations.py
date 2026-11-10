"""Validated create and update operations (no direct ad hoc ledger edits)."""

from datetime import datetime, timezone
from pathlib import Path

from .audit import append_event
from .catalog import load_catalog
from .identity import identifier
from .permissions import require_writer
from .storage import save


def timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("event timestamp must be UTC ISO8601")
    return value


def new(root: Path, base_ref: str, *, topic: str, created_on: str,
        sources: list[str], evidence: str, recommendation: str,
        triage_rationale: str, policy_version: str,
        duplicate_reason: str = "", related_ids: list[str] | None = None,
        at: str | None = None) -> tuple[str, str]:
    actor = require_writer()
    key = identifier(topic, created_on)
    record = dict(schema_version="advisory/v1", id=key, topic=topic,
                  created_on=created_on, status="open", sources=sources,
                  evidence=evidence, recommendation=recommendation,
                  triage_rationale=triage_rationale, policy_version=policy_version,
                  related_ids=related_ids or [], duplicate_reason=duplicate_reason,
                  promoted_issue="", base_sha256="", revision=1, history=[])
    append_event(record, "create", "", actor, timestamp(at), "registered")
    return key, save(root, record, expected_sha256=None, base_ref=base_ref)


def modify(root: Path, base_ref: str, key: str, expected_sha256: str,
           action: str, *, at: str | None = None, reason: str,
           changes: dict | None = None) -> str:
    actor = require_writer()
    from .paths import record_path
    from .storage import sha
    path = record_path(root, key)
    if not path.exists() or sha(path.read_bytes()) != expected_sha256:
        raise ValueError("lost update: expected sha256 mismatched")
    record = load_catalog(root)[key]
    previous = record["status"]
    if action == "amend":
        allowed = {"evidence", "recommendation", "triage_rationale",
                   "policy_version", "sources", "related_ids", "duplicate_reason"}
        if not changes or not set(changes) <= allowed:
            raise ValueError("invalid mutable field selection")
        for name in ("sources", "related_ids"):
            if name in changes:
                if not isinstance(changes[name], list):
                    raise ValueError("references must be lists")
                changes[name] = list(dict.fromkeys(record[name] + changes[name]))
        record.update(changes)
    elif action == "transition":
        if set(changes or {}) != {"status"}:
            raise ValueError("transition requires only status")
        record.update(changes)
    elif action == "promote":
        if set(changes or {}) != {"promoted_issue"} or previous != "triaged":
            raise ValueError("promote requires triaged advisory and existing issue")
        record.update(changes)
        record["status"] = "promoted"
    else:
        raise ValueError("unknown advisory operation")
    record["revision"] += 1
    append_event(record, action, previous, actor, timestamp(at), reason)
    return save(root, record, expected_sha256=expected_sha256, base_ref=base_ref)
