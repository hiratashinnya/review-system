"""NFKC+casefold collision checks for immutable ledger identifiers."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from collections.abc import Iterable

from .model_constants import ERROR
from .model_types import Finding

LEDGER_DIRECTORY = ".ai/feedback/ledger"


def normalized_ledger_id(document_id: str) -> str:
    """Normalize an ID for collision comparison without changing its stored form."""
    return unicodedata.normalize("NFKC", document_id).casefold()


def colliding_ledger_ids(candidate: str, existing: Iterable[str]) -> list[str]:
    """Return distinct existing IDs that normalize to the candidate's identity."""
    normalized = normalized_ledger_id(candidate)
    return sorted({
        document_id for document_id in existing
        if document_id != candidate and normalized_ledger_id(document_id) == normalized
    })


def ledger_collision_findings(document_ids: Iterable[str]) -> list[Finding]:
    """Report groups of different ledger IDs with the same compatibility identity."""
    groups: dict[str, set[str]] = defaultdict(set)
    for document_id in document_ids:
        groups[normalized_ledger_id(document_id)].add(document_id)
    return [
        Finding(
            "L1", ERROR, LEDGER_DIRECTORY,
            f"別エントリの id が NFKC+casefold 後に衝突している: {', '.join(sorted(ids))}",
        )
        for ids in groups.values() if len(ids) > 1
    ]
