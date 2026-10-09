"""Normalize and validate one declared feedback document field."""

from __future__ import annotations

import datetime

from .model_constants import ERROR
from .model_types import Finding
from .model_values import _is_plain_date, normalize_line, normalize_strlist, normalize_text
from .schema_types import Field
from .tomlwrite import DATE, INT, LINE, OPTDATE, STRLIST, TEXT

def _normalize_field(field: Field, raw, locus: str, findings: list[Finding]):
    """1つの欄を正規化して返す。値として使えないときは ``None`` を返す。"""
    if field.kind in (LINE,):
        if not isinstance(raw, str):
            findings.append(Finding("L1", ERROR, locus, f"文字列でなければならない: {raw!r}"))
            return None
        value = normalize_line(raw)
        if "\n" in value:
            findings.append(Finding("L1", ERROR, locus, "1行の値に改行を含めてはならない"))
            return None
    elif field.kind == TEXT:
        if not isinstance(raw, str):
            findings.append(Finding("L1", ERROR, locus, f"文字列でなければならない: {raw!r}"))
            return None
        if "'''" in raw:
            findings.append(
                Finding("L1", ERROR, locus, "複数行の値に ''' を含めてはならない")
            )
            return None
        value = normalize_text(raw)
    elif field.kind == INT:
        if isinstance(raw, bool) or not isinstance(raw, int):
            findings.append(Finding("L1", ERROR, locus, f"整数でなければならない: {raw!r}"))
            return None
        if raw < 0:
            findings.append(Finding("L1", ERROR, locus, f"負の整数は使えない: {raw}"))
            return None
        value = raw
    elif field.kind == DATE:
        if not _is_plain_date(raw):
            findings.append(
                Finding("L1", ERROR, locus, f"TOML の日付（YYYY-MM-DD）でなければならない: {raw!r}")
            )
            return None
        value = raw
    elif field.kind == OPTDATE:
        if raw == "":
            value = ""
        elif _is_plain_date(raw):
            value = raw
        else:
            findings.append(
                Finding("L1", ERROR, locus,
                        f"日付（YYYY-MM-DD）または空文字でなければならない: {raw!r}")
            )
            return None
    elif field.kind == STRLIST:
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            findings.append(
                Finding("L1", ERROR, locus, f"文字列の配列でなければならない: {raw!r}")
            )
            return None
        value = normalize_strlist(raw)
    else:  # pragma: no cover - schema 側のプログラミングエラー
        raise ValueError(f"未知の値種別: {field.kind}")

    empty = value in ("", [], 0)
    if field.required_nonempty and empty:
        findings.append(Finding("L1", ERROR, locus, "必須の欄が空になっている"))
        return value
    if empty:
        return value

    if field.enum is not None and value not in field.enum:
        findings.append(
            Finding("L1", ERROR, locus,
                    f"語彙外の値: {value!r}（許可: {', '.join(field.enum)}）")
        )
    if field.pattern is not None:
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not field.pattern.match(item):
                findings.append(
                    Finding("L1", ERROR, locus,
                            f"書式に合わない値: {item!r}（期待: {field.pattern.pattern}）")
                )
    return value
