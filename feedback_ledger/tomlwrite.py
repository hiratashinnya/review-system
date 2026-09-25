"""canonical TOML の最小シリアライザ（読みは標準の :mod:`tomllib`）。

**なぜ自前で書くのか**（オーナー確定・2026-09-19）:
  * 標準ライブラリの :mod:`tomllib` は **読み専用**（``load``/``loads`` のみ。``dump``/``dumps``
    は存在しない）。
  * ``tomli_w``/``toml``/``tomlkit`` はいずれも未インストールで、本リポジトリには依存
    マニフェストが無く既存ハーネスは全件が標準ライブラリのみで動く。**サードパーティ依存を
    追加しない**方針をここでも守る。
  * L7（canonical 検査＝パース→再シリアライズ→バイト比較）の安定性は「出力バイト列の決定権を
    自分で持つ」ことが根拠になる。外部ライブラリだと版が上がるたびに canonical の定義が動き、
    リポジトリ側の変更ゼロで CI が赤くなりうる。

**扱う TOML の部分集合**（これ以外は書けない＝書けない形は仕様上存在しない）:
  * トップレベルのキー・値、``[table]``、``[[array of tables]]``（1段のみ・入れ子なし）
  * 値の型は ``line``（1行文字列）／``text``（複数行リテラル文字列 ``'''``）／``int``／
    ``date``（TOML local date）／``optdate``（date または空文字）／``strlist``（文字列配列）

**canonical の定義**（決定論的であることが要件）:
  * キーの並びは :mod:`feedback_ledger.schema` の宣言順に固定する（入力の並びは使わない）。
  * テーブルは宣言順に出力し、その直前に空行を1つ置く。
  * 文書は改行1つで終わる。
  * 1行文字列は basic string（``"..."``）、複数行は literal string（``'''``）で出力する。
    literal string は**エスケープを持たない**ため、``'''`` や ``\\r`` を含む値は
    :class:`TomlWriteError` で拒否する（表現できない値を黙って壊さない）。

依存仕様: Issue #522「Scope / lint 規則 L7」。
"""

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
    """canonical TOML として表現できない値。"""


_BASIC_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def escape_basic(value: str) -> str:
    """basic string（``"..."``）の中身をエスケープする。"""
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
    """1つの値を canonical な TOML 表記へ変換する。"""
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
            # 空の複数行値は `''''''` にせず、1行リテラルの空文字で表す（読みやすさ）。
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


def dumps(spec, data: dict) -> str:
    """``spec``（:class:`feedback_ledger.schema.DocSpec`）の宣言順に canonical TOML を組む。"""
    lines: list[str] = []
    for table in spec.tables:
        if table.name == "":
            for field in table.fields:
                lines.append(f"{field.name} = {render_value(field.kind, data[field.name])}")
            continue
        if table.repeated:
            if not data[table.name]:
                # TOML の `[[name]]` 記法では**空の配列を書けない**。空のときだけ root テーブルの
                # キーとして `name = []` を出す（root のキーは表ヘッダより前に置く必要があるため、
                # 直前のトップレベル走査の続きとして改行だけで繋ぐ）。
                lines.append(f"{table.name} = []")
                continue
            for item in data[table.name]:
                lines.append("")
                lines.append(f"[[{table.name}]]")
                for field in table.fields:
                    lines.append(f"{field.name} = {render_value(field.kind, item[field.name])}")
            continue
        lines.append("")
        lines.append(f"[{table.name}]")
        for field in table.fields:
            body = data[table.name][field.name]
            lines.append(f"{field.name} = {render_value(field.kind, body)}")
    return "\n".join(lines) + "\n"
