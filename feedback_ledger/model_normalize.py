"""Normalize a complete document against its schema declaration."""

from __future__ import annotations

from .model_constants import ERROR
from .model_field import _normalize_field
from .model_subtable import _normalize_subtable
from .model_types import Finding
from .schema_types import DocSpec
from .schema_version import is_legacy_ledger_without_theme

def normalize_document(spec: DocSpec, raw: dict, locus: str) -> tuple[dict | None, list[Finding]]:
    """L1／L4／L5 を検査しつつ canonical な内部表現へ正規化する。

    戻り値の ``data`` は「シリアライズできる形」まで揃ったときだけ非 ``None`` になる
    （キーが欠けている・型が違う欄があると ``None``）。``findings`` は空でなくても
    ``data`` が返ることがある（enum 違反など、値としては書けるが規則違反である場合）。
    """
    findings: list[Finding] = []
    if not isinstance(raw, dict):
        findings.append(Finding("L1", ERROR, locus, "トップレベルがテーブルでない"))
        return None, findings

    document_id = raw.get("id") if isinstance(raw.get("id"), str) else locus
    data: dict = {}
    complete = True

    declared_tables = {table.name for table in spec.tables if table.name}
    top_fields = {field.name for table in spec.tables if not table.name for field in table.fields}
    unknown_top = sorted(set(raw) - top_fields - declared_tables)
    for key in unknown_top:
        findings.append(Finding("L1", ERROR, f"{locus}::{key}", "宣言されていないキー"))

    for table in spec.tables:
        if not table.name:
            for field in table.fields:
                where = f"{locus}::{field.name}"
                if field.name not in raw:
                    may_omit_theme = (
                        spec.kind == "ledger" and field.name == "theme"
                        and is_legacy_ledger_without_theme(raw.get("schema"))
                    )
                    if may_omit_theme:
                        continue
                    findings.append(Finding("L1", ERROR, where, "必須のキーが無い"))
                    complete = False
                    continue
                value = _normalize_field(field, raw[field.name], where, findings)
                if value is None:
                    complete = False
                    continue
                data[field.name] = value
            continue

        if table.name not in raw:
            findings.append(
                Finding("L1", ERROR, f"{locus}::[{table.name}]", "必須のテーブルが無い")
            )
            complete = False
            continue

        section = raw[table.name]
        if table.repeated:
            if not isinstance(section, list):
                findings.append(Finding(
                    "L1", ERROR, f"{locus}::[[{table.name}]]",
                    "テーブルの配列でなければならない",
                ))
                complete = False
                continue
            if len(section) < table.min_items:
                findings.append(Finding(
                    "L1", ERROR, f"{locus}::[[{table.name}]]",
                    f"要素数が下限未満: {len(section)}（最小: {table.min_items}）",
                ))
            items = []
            for index, element in enumerate(section):
                item, ok = _normalize_subtable(
                    table, element, f"{locus}::[[{table.name}]][{index}]",
                    document_id, findings,
                )
                complete = complete and ok
                if ok:
                    items.append(item)
            items.sort(key=lambda entry: tuple(str(entry[f.name]) for f in table.fields))
            data[table.name] = items
            continue

        item, ok = _normalize_subtable(
            table, section, f"{locus}::[{table.name}]", document_id, findings
        )
        complete = complete and ok
        if ok:
            data[table.name] = item

    if not complete:
        return None, findings
    return data, findings
