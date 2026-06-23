"""ノードの YAML ブロック専用の最小サブセットリーダ。

doc-system のノードは ``<details>`` 内の ```yaml``` ブロックに以下しか書かない（04-notation §3）:
  * 平坦な ``key: value`` スカラ（引用/非引用・int・bool・null）
  * 空/インラインのフローリスト（``labels: []`` / ``suppress: [RULE-018]``）
  * ``edges:`` ブロックリスト（``- to:`` ＋ ``ref_version:`` ＋任意の ``note:``）

汎用 YAML パーサは持ち込まず、この限定文法だけを扱う。``review_system/parsing/frontmatter.py``
と同じ mini-YAML 思想だが、プロダクトパッケージへ依存しないよう独立実装する。
"""

from __future__ import annotations

import re
from typing import Any

_INT_RE = re.compile(r"-?\d+")


class NodeYamlError(ValueError):
    """ノード YAML ブロックがこのサブセット文法でパースできないとき送出する。"""

    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__(f"line {line_no}: {reason}")
        self.line_no = line_no
        self.reason = reason


def _strip_inline_comment(s: str) -> str:
    """引用符の外にある ``#`` 以降をコメントとして除去する。"""
    quote: str | None = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i]
    return s


def _scalar(raw: str) -> Any:
    """スカラ文字列を Python 値へ変換する（引用除去・bool/int/null 認識）。"""
    s = _strip_inline_comment(raw).strip()
    if s == "":
        return ""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    if s == "true":
        return True
    if s == "false":
        return False
    if s in ("null", "~"):
        return None
    if _INT_RE.fullmatch(s):
        return int(s)
    return s


def _inline_list(raw: str) -> list[Any]:
    """``[a, b, c]`` 形式のインラインフローリストを解釈する（空 ``[]`` 含む）。"""
    s = _strip_inline_comment(raw).strip()
    inner = s[1:-1].strip()
    if inner == "":
        return []
    return [_scalar(part) for part in inner.split(",")]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_edges(lines: list[str], start: int) -> tuple[list[dict[str, Any]], int]:
    """``edges:`` 直後のブロックリストを読み、(edges, 次行index) を返す。

    依存仕様: 04-notation.md §3（`to` スカラ・`ref_version` 必須・`note` 任意・`kind`/`status` なし）。
    """
    edges: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    i = start
    while i < len(lines):
        line = lines[i]
        if line.strip() == "" or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line) == 0:  # ブロック終端（トップレベルへ戻った）
            break
        body = line.strip()
        if body.startswith("- "):
            current = {}
            edges.append(current)
            body = body[2:].strip()
            if body:
                key, sep, val = body.partition(":")
                if not sep:
                    raise NodeYamlError(i + 1, f"edge 行に ':' がない: {body!r}")
                current[key.strip()] = _scalar(val)
        else:
            if current is None:
                raise NodeYamlError(i + 1, f"'- to:' より前の edge 属性: {body!r}")
            key, sep, val = body.partition(":")
            if not sep:
                raise NodeYamlError(i + 1, f"edge 属性行に ':' がない: {body!r}")
            current[key.strip()] = _scalar(val)
        i += 1
    return edges, i


def parse(text: str) -> dict[str, Any]:
    """ノードの YAML ブロック本文（フェンス内）を dict へパースする。

    依存仕様: 04-notation.md §3（YAML ブロック文法・edge スキーマ）。
      記法が崩れた YAML をパースできない場合に失敗する点＝SPEC-2 v0.3.0（呼び出し側が fail-soft 化）。
    """
    lines = text.splitlines()
    data: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "" or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line) != 0:
            raise NodeYamlError(i + 1, f"想定外のインデント: {line!r}")
        key, sep, rest = line.strip().partition(":")
        if not sep:
            raise NodeYamlError(i + 1, f"':' がない行: {line!r}")
        key = key.strip().strip("\"'")
        rest = rest.strip()
        if key == "edges" and rest == "":
            data["edges"], i = _parse_edges(lines, i + 1)
            continue
        if rest == "":
            data[key] = ""
        elif rest.startswith("["):
            data[key] = _inline_list(rest)
        else:
            data[key] = _scalar(rest)
        i += 1
    return data
