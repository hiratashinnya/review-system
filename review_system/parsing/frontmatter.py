"""自前フロントマター・パーサ（mini-YAML サブセット）。

[schema 対応文法](../../docs/schema/README.md)・[Q5a](../../docs/dashboard.md)・[DD7](../../docs/design/decisions.md)。
パーサ＝検証器（S5）。**対応サブセット外は黙って通さず MiniYamlError で実行前 fail-close**。

対応：マッピング `key: value`（key は小文字スネーク、または引用文字列 `"*"`/`'…'`）／ブロック列 `- `／
スカラ（素文字列・"…"・'…'・10進整数・true/false・null）／行・行末コメント（引用内 `#` は除く）／
インデントは半角スペース2刻みのみ（タブ禁止）。ブロックのマッピング入れ子は深さ任意（policy の matrix で3段）。
非対応（=エラー）：フロー `[]{}`・アンカー/エイリアス `&*`・複数行 `|>`・タグ `!!`・マージ `<<`・
複数ドキュメント・3スペース等の奇数インデント・閉じ `---` 欠落。

版（version）は `"MAJOR.MINOR"` 文字列で読む（整数化しない）。MAJOR 対応判定は lint が行う。
"""
from __future__ import annotations

import re

KEY = re.compile(r"([a-z_][a-z0-9_]*):(.*)$")
_INT = re.compile(r"-?\d+$")


class MiniYamlError(Exception):
    """対応サブセット外・構文不正。`line_no`（1始まり）と理由を持つ（O-14 素材）。"""

    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__(f"L{line_no}: {reason}")
        self.line_no = line_no
        self.reason = reason


def parse_frontmatter(text: str, is_markdown: bool) -> dict:
    """フロントマター（.md は先頭 `---`…`---`／.yaml は全体）を dict に読む。"""
    body_lines = _extract_body(text, is_markdown)
    entries = _tokenize(body_lines)
    value, idx = _parse_block(entries, 0, 0)
    if idx != len(entries):
        raise MiniYamlError(entries[idx][0], "解釈できない行（構造の不整合）")
    return value if isinstance(value, dict) else {}


def _extract_body(text: str, is_markdown: bool) -> list[tuple[int, str]]:
    """(line_no, raw_line) のリストを返す。md は最初の `---`…`---` 間だけ。"""
    raw = text.splitlines()
    if not is_markdown:
        return list(enumerate(raw, start=1))
    # 先頭の `---`
    i = 0
    while i < len(raw) and raw[i].strip() == "":
        i += 1
    if i >= len(raw) or raw[i].strip() != "---":
        raise MiniYamlError(i + 1, "フロントマターは先頭の `---` で始まる必要がある")
    start = i + 1
    for j in range(start, len(raw)):
        if raw[j].strip() == "---":
            return list(enumerate(raw[start:j], start=start + 1))
    raise MiniYamlError(len(raw), "閉じの `---` が無い（複数行/未終端）")


def _tokenize(lines: list[tuple[int, str]]) -> list[tuple[int, int, str]]:
    """(line_no, indent, content) の並び。空行/全行コメントは捨て、行末コメントは除去。"""
    out: list[tuple[int, int, str]] = []
    for line_no, raw in lines:
        if "\t" in (raw[: len(raw) - len(raw.lstrip(" \t"))]):
            raise MiniYamlError(line_no, "タブインデントは非対応（半角スペース2刻みのみ）")
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw[indent:]
        if content.strip() == "" or content.lstrip().startswith("#"):
            continue
        if indent % 2 != 0:
            raise MiniYamlError(line_no, f"インデントは2の倍数のみ（{indent} スペース）")
        out.append((line_no, indent, _strip_inline_comment(content)))
    return out


def _strip_inline_comment(s: str) -> str:
    quote: str | None = None
    out: list[str] = []
    for i, c in enumerate(s):
        if quote:
            out.append(c)
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            out.append(c)
        elif c == "#" and (i == 0 or s[i - 1].isspace()):
            break
        else:
            out.append(c)
    return "".join(out).rstrip()


def _split_key_value(content: str, line_no: int) -> tuple[str, str]:
    """`key: value` を分割。key は小文字スネーク、または引用文字列（`"*"` 等・Q24=A）。"""
    if content[0] in "\"'":
        q = content[0]
        end = content.find(q, 1)
        if end == -1:
            raise MiniYamlError(line_no, "閉じられていないキーの引用符")
        after = content[end + 1:].lstrip()
        if not after.startswith(":"):
            raise MiniYamlError(line_no, "引用キーの後に `:` が無い")
        return content[1:end], after[1:].strip()
    m = KEY.match(content)
    if not m:
        raise MiniYamlError(line_no, f"`key: value` 形式でない（非対応記法）: {content!r}")
    return m.group(1), m.group(2).strip()


def _looks_like_key(content: str) -> bool:
    return bool(KEY.match(content)) or (bool(content) and content[0] in "\"'")


def _parse_block(entries, i: int, indent: int):
    if i >= len(entries):
        return {}, i
    content = entries[i][2]
    if content == "-" or content.startswith("- "):
        return _parse_list(entries, i, indent)
    return _parse_mapping(entries, i, indent)


def _parse_mapping(entries, i: int, indent: int):
    result: dict = {}
    while i < len(entries):
        line_no, ind, content = entries[i]
        if ind < indent:
            break
        if ind > indent:
            raise MiniYamlError(line_no, "想定外の深いインデント")
        if content.startswith("- "):
            raise MiniYamlError(line_no, "マッピング中にブロック列が現れた")
        key, rest = _split_key_value(content, line_no)
        if rest == "":
            if i + 1 < len(entries) and entries[i + 1][1] > indent:
                child, i = _parse_block(entries, i + 1, entries[i + 1][1])
                result[key] = child
            else:
                result[key] = None
                i += 1
        else:
            result[key] = _parse_scalar(rest, line_no)
            i += 1
    return result, i


def _parse_list(entries, i: int, indent: int):
    items: list = []
    item_indent = indent + 2
    while i < len(entries):
        line_no, ind, content = entries[i]
        if ind != indent or not (content == "-" or content.startswith("- ")):
            break
        first = content[2:].strip() if content.startswith("- ") else ""
        sub: list = []
        if first:
            sub.append((line_no, item_indent, first))
        j = i + 1
        while j < len(entries) and entries[j][1] >= item_indent:
            sub.append(entries[j])
            j += 1
        if sub and _looks_like_key(sub[0][2]):   # mapping 要素
            value, _ = _parse_mapping(sub, 0, item_indent)
        elif first:                              # scalar 要素
            value = _parse_scalar(first, line_no)
        else:
            raise MiniYamlError(line_no, "空のリスト要素")
        items.append(value)
        i = j
    return items, i


def _parse_scalar(s: str, line_no: int):
    if s[0] in "[{":
        raise MiniYamlError(line_no, "フロースタイル `[]`/`{}` は非対応")
    if s[0] in "&*":
        raise MiniYamlError(line_no, "アンカー/エイリアス `&`/`*` は非対応")
    if s[0] in "|>":
        raise MiniYamlError(line_no, "複数行スカラ `|`/`>` は非対応")
    if s.startswith("!!") or s.startswith("<<"):
        raise MiniYamlError(line_no, "タグ/マージキーは非対応")
    if s[0] in "\"'":
        if len(s) >= 2 and s[-1] == s[0]:
            return s[1:-1]
        raise MiniYamlError(line_no, "閉じられていない引用符")
    if s == "null":
        return None
    if s in ("true", "false"):
        return s == "true"
    if _INT.match(s):
        return int(s)
    return s
