"""Narrative vocabulary checks for L4 and L5."""

from __future__ import annotations

from .allowlist import is_allowlisted
from .model_constants import ASSERTION_TERMS, ERROR, INFERRED_MARKER, SPECULATION_TERMS
from .model_types import Finding
from .schema_types import Field

def _lint_narrative(document_id, field: Field, value: str, locus, findings):
    """L4／L5（語彙 lint）。誤検出は allowlist で理由付きに抑制する。"""
    if not value:
        return
    if field.lint == "owner-verbatim":
        for term in SPECULATION_TERMS:
            if term in value:
                if is_allowlisted(document_id, "L4", term, value):
                    continue
                findings.append(Finding(
                    "L4", ERROR, locus,
                    f"逐語引用の欄に推測語彙 {term!r} が混ざっている"
                    "（解釈は inferred_reason へ分ける。不可避なら"
                    " feedback_ledger/allowlist.py へ理由付きで登録する）",
                ))
    elif field.lint == "inferred":
        if not value.startswith(INFERRED_MARKER):
            findings.append(Finding(
                "L5", ERROR, locus,
                f"推論の欄は {INFERRED_MARKER!r} で始めなければならない"
                "（引用と推論を読み手が区別できるようにするため）",
            ))
        for term in ASSERTION_TERMS:
            if term in value:
                if is_allowlisted(document_id, "L5", term, value):
                    continue
                findings.append(Finding(
                    "L5", ERROR, locus,
                    f"推論の欄に断定語彙 {term!r} が使われている"
                    "（発言として記録できるのは owner_verbatim だけ）",
                ))
