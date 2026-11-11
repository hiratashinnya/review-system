"""Canonical TOML field contract; unknown keys fail closed."""

FIELDS = (
    "schema_version", "id", "topic", "created_on", "status", "sources",
    "evidence", "recommendation", "triage_rationale", "policy_version",
    "related_ids", "duplicate_reason", "promoted_issue", "base_sha256", "revision",
    "history",
)
EVENT_FIELDS = (
    "action", "from_status", "to_status", "actor", "at", "reason", "policy_version",
    "previous", "payload_digest", "digest",
)
STATES = ("open", "triaged", "promoted", "closed")
MOVES = {
    "open": {"triaged", "closed"},
    "triaged": {"open", "promoted", "closed"},
    "promoted": {"closed"},
    "closed": {"open"},
}
CHANGERS = {"create", "amend", "transition", "promote"}
