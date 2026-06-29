"""行配列に対する純粋な編集ヘルパと、複数編集の一括適用。

各ヘルパは「対象行（群）→ 置換行（群）」を返すだけの純関数で、ファイル全体の splice は
:func:`apply_edits` が担う。編集はインデックスを後ろから適用するため互いの位置をずらさない。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import BackrefError

_VERSION_RE = re.compile(r"v(\d+\.\d+\.\d+)")


@dataclass(frozen=True)
class Edit:
    """``lines[start:end+1]`` を ``new`` で置換する編集（``start``/``end`` は 0 始まり inclusive）。"""

    start: int
    end: int
    new: list[str]
    label: str = ""


def bump_summary_z(line: str) -> str:
    """summary 行の ``vX.Y.Z`` の z を +1 した行を返す（DD-8 §4: backref 追加＝z）。"""
    m = _VERSION_RE.search(line)
    if not m:
        raise BackrefError(f"summary 行にバッジ vX.Y.Z が無い: {line!r}")
    x, y, z = m.group(1).split(".")
    new_badge = f"v{x}.{y}.{int(z) + 1}"
    return line[: m.start()] + new_badge + line[m.end() :]


def xy(version: str) -> str:
    """``X.Y.Z`` バッジから ``X.Y``（ref_version の比較単位）を返す。"""
    parts = version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else version


def render_edge_entry(to: str, ref_version: str, dash_indent: int = 2) -> list[str]:
    """1 本の依存辺を block list 項目（2 行）に整形する。"""
    pad = " " * dash_indent
    attr_pad = " " * (dash_indent + 2)
    return [f"{pad}- to: {to}", f'{attr_pad}ref_version: "{ref_version}"']


def set_resolved_true_line(line: str) -> str:
    """既存の ``resolved:`` 行の値を true にする（インデント保持）。"""
    indent = line[: len(line) - len(line.lstrip(" "))]
    return f"{indent}resolved: true"


def apply_edits(lines: list[str], edits: list[Edit]) -> list[str]:
    """同一ファイルへの複数 :class:`Edit` を適用した新しい行配列を返す。

    後ろ（大きい index）から splice するため、各編集の位置は互いにずれない。
    範囲が重なる編集が含まれていれば :class:`BackrefError`（呼び出し側の組み立てミス）。
    """
    ordered = sorted(edits, key=lambda e: e.start, reverse=True)
    prev_start = len(lines) + 1
    out = list(lines)
    for e in ordered:
        if e.start < 0 or e.end >= len(lines) + 1 or e.start > e.end + 1:
            raise BackrefError(f"不正な編集範囲: start={e.start} end={e.end}（{e.label}）")
        if e.end >= prev_start:
            raise BackrefError(f"編集範囲が重複している（{e.label}）")
        prev_start = e.start
        out[e.start : e.end + 1] = e.new
    return out
