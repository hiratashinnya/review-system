"""Canonical TOML value rendering primitives."""

from __future__ import annotations

import datetime

LINE = "line"
TEXT = "text"
INT = "int"
DATE = "date"
OPTDATE = "optdate"
STRLIST = "strlist"

VALUE_KINDS = (LINE, TEXT, INT, DATE, OPTDATE, STRLIST)


class TomlWriteError(ValueError):
    """Canonical TOML cannot represent a supplied value."""


_BASIC_ESCAPES = {
    "\\": "\\\\", '"': '\\"', "\b": "\\b", "\t": "\\t",
    "\n": "\\n", "\f": "\\f", "\r": "\\r",
}


def escape_basic(value: str) -> str:
    """Escape a value for a TOML basic string."""
    out: list[str] = []
    for char in value:
        if char in _BASIC_ESCAPES:
            out.append(_BASIC_ESCAPES[char])
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append("\\u%04X" % ord(char))
        else:
            out.append(char)
    return "".join(out)


def render_value(kind: str, value) -> str:
    """Render one supported Python value as canonical TOML."""
    if kind == LINE:
        if not isinstance(value, str):
            raise TomlWriteError(f"line には文字列が必要: {value!r}")
        if "\n" in value or "\r" in value:
            raise TomlWriteError("line に改行は書けない（複数行は text を使う）")
        return f'"{escape_basic(value)}"'
    if kind == TEXT:
        if not isinstance(value, str):
            raise TomlWriteError(f"text には文字列が必要: {value!r}")
        if value == "":
            # Empty multiline text uses a single-line literal string.
            return "''"
        if "'''" in value:
            raise TomlWriteError("text に ''' は書けない（リテラル文字列の終端と衝突する）")
        if "\r" in value:
            raise TomlWriteError("text に CR は書けない（LF へ正規化すること）")
        if not value.endswith("\n"):
            raise TomlWriteError("text は正規化済み（末尾が改行1つ）でなければならない")
        return "'''\n" + value + "'''"
    if kind == INT:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TomlWriteError(f"int には整数が必要: {value!r}")
        return str(value)
    if kind in (DATE, OPTDATE):
        if kind == OPTDATE and value == "":
            return '""'
        if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
            raise TomlWriteError(f"{kind} には datetime.date が必要: {value!r}")
        return value.isoformat()
    if kind == STRLIST:
        if not isinstance(value, (list, tuple)):
            raise TomlWriteError(f"strlist には配列が必要: {value!r}")
        items = []
        for item in value:
            if not isinstance(item, str):
                raise TomlWriteError(f"strlist の要素は文字列: {item!r}")
            if "\n" in item or "\r" in item:
                raise TomlWriteError("strlist の要素に改行は書けない")
            items.append(f'"{escape_basic(item)}"')
        return "[" + ", ".join(items) + "]"
    raise TomlWriteError(f"未知の値種別: {kind!r}")
