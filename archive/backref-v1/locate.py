"""ノードの summary 行から YAML フェンス・``edges:`` ブロック・本文範囲を行単位で特定する。

docidx は file:line（summary 行）までは教えてくれるが、書込のための**正確な行範囲**は持たない。
ここでは対象ファイルを行配列として読み直し、編集対象の範囲を 0 始まりインデックスで返す。
想定形（``⬡ ID · vX.Y.Z`` summary／直後の ```yaml フェンス／indent 0 の ``edges:``／
2スペース ``- to:`` block list か ``edges: []``）から外れたら :class:`BackrefError` で停止する。

依存仕様: SPEC-1 v0.3.0・SPEC-1-1 v0.1.1（ノード発見・summary→フェンス・本文範囲＝`</details>` 後）・
  SPEC-2 v0.3.0（edges ブロック文法）。補助（out-of-graph・版なし）: 04-notation §3,§8・02-meta-schema §4。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import BackrefError

_SUMMARY = "⬡"
_MIDDOT = "·"
_VERSION_RE = re.compile(r"v(\d+\.\d+\.\d+)")


def _is_summary_line(line: str) -> bool:
    return "<summary" in line and _SUMMARY in line and _MIDDOT in line


def _is_boundary(line: str) -> bool:
    s = line.strip()
    return s == "---" or s.startswith("## ") or _is_summary_line(line)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


@dataclass(frozen=True)
class YamlBlock:
    """ノードの YAML フェンスの位置（``fence_open``/``fence_close`` は ``` 行そのもの）。"""

    fence_open: int  # ```yaml 行の index
    fence_close: int  # 閉じ ``` 行の index
    summary_idx: int


@dataclass(frozen=True)
class EdgesSpan:
    """YAML ブロック内の ``edges:`` の行範囲（``start``〜``end`` は inclusive・0 始まり）。"""

    start: int
    end: int
    inline: bool  # True なら ``edges: []`` / ``edges: [..]`` の 1 行形
    entry_indent: int  # block 形のとき ``- to:`` のインデント（既定 2）
    inline_empty: bool = False  # inline のとき ``edges: []``（空）か ``edges: [..]``（非空）か


@dataclass(frozen=True)
class BodyRegion:
    """``</details>`` の次行から次境界の手前までの本文範囲（``start``〜``end`` inclusive）。

    本文が空のときは ``start > end``（挿入位置は ``start``）。
    """

    start: int
    end: int


def find_yaml_block(lines: list[str], summary_idx: int, node_id: str) -> YamlBlock:
    """summary 行（0 始まり index）から直後の ```yaml フェンスを特定する。"""
    if summary_idx < 0 or summary_idx >= len(lines):
        raise BackrefError(f"{node_id}: summary 行 index={summary_idx} が範囲外")
    if not _is_summary_line(lines[summary_idx]):
        raise BackrefError(
            f"{node_id}: index={summary_idx} は summary 行でない: {lines[summary_idx]!r}"
        )
    n = len(lines)
    i = summary_idx + 1
    while i < n and not lines[i].strip().startswith("```"):
        if _is_boundary(lines[i]):
            raise BackrefError(f"{node_id}: YAML フェンス開始前に境界に到達した")
        i += 1
    if i >= n:
        raise BackrefError(f"{node_id}: YAML フェンス開始（```）が見つからない")
    fence_open = i
    j = i + 1
    while j < n and not lines[j].strip().startswith("```"):
        j += 1
    if j >= n:
        raise BackrefError(f"{node_id}: YAML フェンス終了（```）が見つからない")
    return YamlBlock(fence_open=fence_open, fence_close=j, summary_idx=summary_idx)


def find_key_line(lines: list[str], block: YamlBlock, key: str) -> int | None:
    """YAML ブロック内で indent 0 の ``key:`` 行 index を返す（無ければ None）。"""
    for i in range(block.fence_open + 1, block.fence_close):
        line = lines[i]
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue
        if _indent(line) != 0:
            continue
        k = line.split(":", 1)[0].strip().strip("\"'")
        if k == key:
            return i
    return None


def find_edges_span(lines: list[str], block: YamlBlock) -> EdgesSpan | None:
    """``edges:`` の行範囲を特定する（無ければ None）。"""
    key_idx = find_key_line(lines, block, "edges")
    if key_idx is None:
        return None
    rest = lines[key_idx].split(":", 1)[1].strip()
    if rest != "":
        # ``edges: []`` / ``edges: [..]`` の inline 1 行形。空かどうかを区別する
        # （非空 inline への追記は既存辺を壊すため、呼び出し側で fail-close させる）。
        empty = rest.startswith("[") and rest.rstrip().endswith("]") and rest[1:-1].strip() == ""
        return EdgesSpan(start=key_idx, end=key_idx, inline=True, entry_indent=2,
                         inline_empty=empty)
    # block 形: 後続の indent>0 行を消費（fence 手前 / indent 0 / 境界で終端）
    end = key_idx
    entry_indent = 2
    found_entry = False
    i = key_idx + 1
    while i < block.fence_close:
        line = lines[i]
        if line.strip() == "" or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line) == 0:
            break
        if not found_entry:
            entry_indent = _indent(line)
            found_entry = True
        end = i
        i += 1
    if not found_entry:
        # ``edges:`` の後に空の block（属性無し）= 想定外。空 [] と等価扱いで inline 化させない。
        raise BackrefError("edges: の後にブロック項目も [] も無い（想定外フォーマット）")
    return EdgesSpan(start=key_idx, end=end, inline=False, entry_indent=entry_indent)


def edge_targets(lines: list[str], span: EdgesSpan) -> set[str]:
    """``edges:`` ブロック内の ``to:`` 値集合を返す（冪等判定用）。"""
    if span.inline:
        return set()
    out: set[str] = set()
    for i in range(span.start + 1, span.end + 1):
        s = lines[i].strip()
        if s.startswith("- "):
            s = s[2:].strip()
        if s.startswith("to:"):
            out.add(s.split(":", 1)[1].strip().strip("\"'"))
    return out


def find_body_region(lines: list[str], summary_idx: int) -> BodyRegion:
    """``</details>`` 以降〜次境界手前の本文範囲を返す。"""
    n = len(lines)
    d = summary_idx
    while d < n and lines[d].strip() != "</details>":
        d += 1
    if d >= n:
        raise BackrefError(f"summary index={summary_idx}: </details> が見つからない")
    start = d + 1
    b = start
    while b < n and not _is_boundary(lines[b]):
        b += 1
    return BodyRegion(start=start, end=b - 1)
