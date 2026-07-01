r"""ノード本文中の孤立 ``---``（ノード分離記法の本文内誤用）の監査。

``04-notation.md`` / ``SCM-1-2`` は ``---`` を「複数ノードを同一ファイルに置く場合の
**ノード分離専用**」記法と規定する。ノード本文中に孤立 ``---`` 行を書くと、
``docidx/scan.py`` / ``backref/locate.py`` の ``_is_boundary`` がそこをノード境界とみなして
本文を silent に截断し、それ以降の本文（``**指摘時 ref_version**:`` 行や論点・選択肢など）が
ノードの ``body`` から静かに脱落する（データ欠落）。実例: FND-94（是正済み）・Q-6。

本モジュールは in-graph ファイルを走査し、ノード分離でも inter-node 注記でもない
本文内 ``---`` を WARNING として列挙する（read-only）。

検出定義（SPEC-62-2）: bare ``---`` 行のうち、**直後の非空行**が
  (a) 見出し ``^#{2,}\s`` / (b) ``<details>`` ・ ``<summary>`` / (c) blockquote ``^>``
のいずれでもないもの＝ノード分離でも inter-node 注記でもない本文内の ``---``。
※ (c) を除外するのは inter-node の削除注記（``> **X は削除**``）を誤検出しないため。
  その代償として「本文内 ``---`` の直後が blockquote」のケースは検出しない（既知の限界）。

依存仕様: SPEC-62 v0.1.0（本文中孤立 ``---`` の検査アンブレラ）・SPEC-62-1 v0.1.0（正常系＝
  本文内孤立 ``---`` が存在しない）・SPEC-62-2 v0.1.0（検出時 WARNING 出力・検出定義）。
  補助（out-of-graph・版なし）: 04-notation.md（``---``=ノード分離）・SCM-1-2 ノードファイル記法スキーマ。
"""

from __future__ import annotations

import re
from pathlib import Path

from .check import Finding

_HEADING = re.compile(r"^#{2,}\s")
_SUMMARY = "⬡"
_MIDDOT = "·"


def _is_node_summary(line: str) -> bool:
    """本物のノード summary 行か（`<summary` タグ＋バッジ記号の存在を必須にする）。"""
    return "<summary" in line and _SUMMARY in line and _MIDDOT in line


def _nearest_node_id(lines: list[str], idx: int) -> str:
    """``idx`` 行より上で直近のノード summary の ID を返す（無ければ ``(file)``）。

    截断されるのは「その ``---`` の直前にある（＝直近上方の）ノードの本文」なので、
    截断被害を受けるノードを Finding の主体として指す。
    """
    for i in range(idx - 1, -1, -1):
        if _is_node_summary(lines[i]):
            after = lines[i].split(_SUMMARY, 1)[1]
            nid = after.split(_MIDDOT, 1)[0].strip()
            return nid or "(file)"
    return "(file)"


def check_stray_hr(root: Path, files: list[Path]) -> list[Finding]:
    """in-graph ファイル群を走査し、本文内の孤立 ``---`` を WARNING で列挙する。

    依存仕様: SPEC-62-2 v0.1.0（検出定義・WARNING 出力）。
    """
    out: list[Finding] = []
    for p in files:
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            rel = str(p)
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            if ln.strip() != "---":
                continue
            # 直後の非空行を見る
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j >= len(lines):
                continue  # ファイル末尾の孤立 --- は截断対象なし
            nx = lines[j].strip()
            if _HEADING.match(nx) or nx.startswith("<details") or "<summary" in nx or nx.startswith(">"):
                continue  # ノード分離 or inter-node 注記＝正常
            nid = _nearest_node_id(lines, i)
            out.append(Finding(
                nid, "warning", "stray-hr-in-body",
                "本文中の孤立 '---'（ノード分離記法の本文内誤用）がノード本文を截断する",
                rel, i + 1))
    return out
