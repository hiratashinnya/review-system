"""Normalize one declared table or repeated-table item."""

from __future__ import annotations

from .model_constants import ERROR
from .model_field import _normalize_field
from .model_narrative import _lint_narrative
from .model_types import Finding

def _normalize_subtable(table, section, locus, document_id, findings):
    if not isinstance(section, dict):
        findings.append(Finding("L1", ERROR, locus, "テーブルでなければならない"))
        return None, False
    declared = {field.name for field in table.fields}
    for key in sorted(set(section) - declared):
        findings.append(Finding("L1", ERROR, f"{locus}::{key}", "宣言されていないキー"))
    item = {}
    ok = True
    for field in table.fields:
        where = f"{locus}::{field.name}"
        if field.name not in section:
            findings.append(Finding("L1", ERROR, where, "必須のキーが無い"))
            ok = False
            continue
        value = _normalize_field(field, section[field.name], where, findings)
        if value is None:
            ok = False
            continue
        if field.lint and isinstance(value, str):
            _lint_narrative(document_id, field, value, where, findings)
        item[field.name] = value
    return item, ok
