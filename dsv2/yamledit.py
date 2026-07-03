"""サイドカー（``{slug}.yaml``）への行ベース最小編集ヘルパ（純関数）。

v2 サイドカーは平坦な ``key: value`` ＋ ``edges:`` ブロックリストのみ（docidx.nodeyaml と同じ
限定文法）。汎用 YAML シリアライザを持ち込まず、必要な箇所だけを行単位で書き換える（既存の
コメント等の意図しない破壊を避ける＝PR8）。各関数は新しい行配列を返す純関数。

依存仕様: doc-system-v2/schema/sidecar.schema.json（version=x.y.z・edge=to/ref_version/note）・
  FORMAT.md §版（backref/lifecycle は z バンプ）・§edges（無名依存辺）。
"""

from __future__ import annotations

import re

_VERSION_RE = re.compile(r'^(version:\s*)(["\']?)(\d+\.\d+\.)(\d+)(["\']?)\s*$')
# 行頭の任意インデント＋（任意の ``- ``）＋ ``to:`` ＋値。値はクォート有無どちらも。
_TO_RE = re.compile(r'^(?P<prefix>\s*(?:-\s*)?to:\s*)(?P<val>.+?)\s*$')


class YamlEditError(ValueError):
    """サイドカーが想定文法から外れて機械編集できないとき送出する。"""


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def bump_version_z(lines: list[str]) -> list[str]:
    """``version: x.y.z`` の z を +1 した新しい行配列を返す（クォート様式を保持）。"""
    for idx, ln in enumerate(lines):
        m = _VERSION_RE.match(ln)
        if m:
            out = list(lines)
            out[idx] = f"{m.group(1)}{m.group(2)}{m.group(3)}{int(m.group(4)) + 1}{m.group(5)}"
            return out
    raise YamlEditError("version: x.y.z 行が見つからない")


def edges_index(lines: list[str]) -> int:
    """トップレベル ``edges:`` 行の index（無ければ -1）。"""
    for idx, ln in enumerate(lines):
        if _indent(ln) == 0 and ln.strip().split("#", 1)[0].strip().startswith("edges:"):
            return idx
    return -1


def _edges_block_end(lines: list[str], start: int) -> int:
    """``edges:`` 行（start）直後のブロック（空行 or インデント行）の終端 index（排他）。"""
    j = start + 1
    while j < len(lines) and (lines[j].strip() == "" or _indent(lines[j]) > 0):
        j += 1
    return j


def edge_targets(lines: list[str]) -> list[str]:
    """edges ブロック内の各 ``- to:`` の値（unquote 済み）を列挙する。"""
    i = edges_index(lines)
    if i < 0:
        return []
    out: list[str] = []
    for ln in lines[i + 1:_edges_block_end(lines, i)]:
        m = re.match(r"^\s*-\s*to:\s*(.+?)\s*$", ln)
        if m:
            out.append(_unquote(m.group(1)))
    return out


def set_edges_empty(lines: list[str]) -> list[str]:
    """``edges:`` ブロック全体を ``edges: []`` に置換した新しい行配列を返す。"""
    i = edges_index(lines)
    if i < 0:
        raise YamlEditError("edges: 行が見つからない")
    end = _edges_block_end(lines, i)
    return lines[:i] + ["edges: []"] + lines[end:]


def add_edge(lines: list[str], to: str, ref_version: str) -> tuple[list[str], bool]:
    """無名依存辺 ``- to: <to>`` を edges へ追加する。

    返り値 ``(新 lines, skipped)``。既に同一 ``to`` があれば追加せず ``skipped=True``。
    非空 inline ``edges: [..]``（複数辺を1行に畳んだ形）は既存辺を黙って落とす危険があるため
    fail-close で拒否する（v2 コーパスは block 形＝``edges: []`` か ``edges:``＋``- to:`` のみ）。
    """
    if to in edge_targets(lines):
        return list(lines), True
    i = edges_index(lines)
    if i < 0:
        raise YamlEditError("edges: 行が見つからない")
    inline = lines[i].strip().split(":", 1)[1].strip()
    entry = [f'  - to: "{to}"', f'    ref_version: "{ref_version}"']
    if inline == "" :
        # block 形: 末尾 entry の直後（ブロック終端）に挿入
        end = _edges_block_end(lines, i)
        insert = end
        # 末尾の空行より前に挿入する（ブロック内の trailing 空行を跨がない）
        while insert - 1 > i and lines[insert - 1].strip() == "":
            insert -= 1
        return lines[:insert] + entry + lines[insert:], False
    if inline == "[]":
        # 空 inline を block 形へ展開
        return lines[:i] + ["edges:"] + entry + lines[i + 1:], False
    raise YamlEditError(
        f"非空 inline edges（{lines[i].strip()!r}）への追加は未対応。block 形へ直すこと"
    )


def retarget_edges(lines: list[str], old: str, new: str) -> tuple[list[str], int]:
    """全 ``to:`` 行のうち値が ``old`` のものを ``new`` へ張替える。

    返り値 ``(新 lines, 変更件数)``。クォート様式は元の値に合わせて保持する。
    """
    out: list[str] = []
    changed = 0
    for ln in lines:
        m = _TO_RE.match(ln)
        if m and _unquote(m.group("val")) == old:
            val = m.group("val").strip()
            quote = val[0] if (len(val) >= 2 and val[0] in ("'", '"') and val[-1] == val[0]) else ""
            out.append(f"{m.group('prefix')}{quote}{new}{quote}")
            changed += 1
        else:
            out.append(ln)
    return out, changed
