"""指摘の重複判定。移設した設計理由は .ai/rationale/karte-module-split.md を参照。"""

from __future__ import annotations

import unicodedata

from .value_codec import normalize_locus

SHINGLE_SIZE = 2
DUPLICATE_SIMILARITY_THRESHOLD = 0.6


def normalize_text(value: str) -> str:
    """設計理由は .ai/rationale/karte-module-split.md を参照。"""
    kept = []
    for char in str(value).casefold():
        kept.append(char if unicodedata.category(char)[0] in ("L", "N") else " ")
    return " ".join("".join(kept).split())


def shingles(value: str, size: int = SHINGLE_SIZE) -> frozenset:
    """設計理由は .ai/rationale/karte-module-split.md を参照。"""
    text = normalize_text(value).replace(" ", "")
    if not text:
        return frozenset()
    if len(text) <= size:
        return frozenset([text])
    return frozenset(text[index:index + size] for index in range(len(text) - size + 1))


def _jaccard(left: frozenset, right: frozenset) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def is_same_finding(summary_a: str, locus_a, summary_b: str, locus_b) -> bool:
    """設計理由は .ai/rationale/karte-module-split.md を参照。"""
    if normalize_text(summary_a) and normalize_text(summary_a) == normalize_text(summary_b):
        return True
    set_a = {normalize_text(item) for item in normalize_locus(locus_a) if normalize_text(item)}
    set_b = {normalize_text(item) for item in normalize_locus(locus_b) if normalize_text(item)}
    if set_a & set_b:
        return (
            _jaccard(shingles(summary_a), shingles(summary_b))
            >= DUPLICATE_SIMILARITY_THRESHOLD
        )
    return False
