"""Separate explicit base authorizations from worktree dispatch lifecycle records."""

from .base_error import require


def authorization_records(document):
    records = document.get("base_authorizations", [])
    require(isinstance(records, list) and all(isinstance(item, dict) for item in records),
            "BASE_LEDGER_INVALID")
    return records


def operation_records(document):
    return document["entries"] + authorization_records(document)
