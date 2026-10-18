"""Exact-value narrative exceptions; types preserve the public compatibility API."""

import json
from pathlib import Path

from .allowlist_types import AllowlistEntry, RULES, collapse


ALLOWLIST = tuple(
    AllowlistEntry(**item) for item in json.loads(
        Path(__file__).with_name("migration_allowlist.json").read_text(encoding="utf-8")
    )
)


def is_allowlisted(document_id: str, rule: str, term: str, value: str):
    """(document_id, rule, term, value) に一致する登録があれば返す（無ければ ``None``）。"""
    lowered = collapse(term).casefold()
    body = collapse(value)
    for entry in ALLOWLIST:
        if (
            entry.document_id == document_id
            and entry.rule == rule
            and collapse(entry.term).casefold() == lowered
            and collapse(entry.value) == body
        ):
            return entry
    return None
