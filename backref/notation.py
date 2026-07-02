r"""ノード本文中の孤立 ``---``（ノード分離記法の本文内誤用）の監査。

``04-notation.md`` / ``SCM-1-2`` は ``---`` を「複数ノードを同一ファイルに置く場合の
**ノード分離専用**」記法と規定する。ノード本文中に孤立 ``---`` 行を書くと、
``docidx/scan.py`` / ``backref/locate.py`` の ``_is_boundary`` がそこをノード境界とみなして
本文を silent に截断し、それ以降の本文（``**指摘時 ref_version**:`` 行や論点・選択肢など）が
ノードの ``body`` から静かに脱落する（データ欠落）。実例: FND-94・Q-6（是正済み）。

本モジュールは in-graph ファイルを走査し、ノード分離でも inter-node 注記でもない
本文内 ``---`` を WARNING として列挙する（read-only）。

検出定義（SPEC-62-2）: bare ``---`` 行のうち、直後の非空行が
  (1) **次ノードの開始**（⬡ バッジ付き ``<summary>`` 行が続くもの＝実パーサの境界）／
  (2) inter-node の blockquote 注記（``^>``・削除注記など）／
  (3) **ノード見出し**（見出し行で、かつ後続に ⬡ バッジ付き ``<summary>`` が続くもの）
のいずれでもないもの＝本文へ流れ込む ``---``。
特に (1)(3) は「⬡ バッジ付き summary（``_is_node_summary_line``）が続くか」で**本物のノード開始**と
**本文（バッジ無しの汎用 ``<details>`` や本文小見出し）**を区別する。実パーサ（``_is_boundary``）の
境界は ``s == "---" or s.startswith("## ") or _is_node_summary_line(line)`` であり、バッジ無しの
汎用 ``<details>`` はノード境界ではない。よって ``---`` はそこで無条件截断し、直後が
バッジ無し ``<details>`` や本文小見出しであっても本文を截断する。
既知の限界: 本文内 ``---`` の直後が blockquote のケースは (2) 除外により検出しない。

依存仕様: SPEC-62 v0.1.0（本文中孤立 ``---`` の検査アンブレラ）・SPEC-62-1 v0.1.0（正常系＝
  本文内孤立 ``---`` が存在しない）・SPEC-62-2 v0.1.1（検出時 WARNING 出力・検出定義）。
  補助（out-of-graph・版なし）: 04-notation.md（``---``=ノード分離）・SCM-1-2 ノードファイル記法スキーマ。
"""

from __future__ import annotations

import re
from pathlib import Path

# ノード summary 判定は docidx の規約実装を再利用する（独自再実装＝規約ドリフトの温床を避ける）。
from docidx.scan import _is_node_summary_line

from .check import Finding

_SUMMARY = "⬡"
_MIDDOT = "·"
_HEADING = re.compile(r"^#{1,}\s")


def _node_summary_starts(lines: list[str], j: int) -> bool:
    """``lines[j]`` から本物のノード（⬡ バッジ付き ``<summary>``）が始まるか。

    実パーサの境界は ``_is_node_summary_line``（⬡ バッジ必須）。バッジ無しの汎用 ``<details>`` は
    ノード境界ではないため、その直前の ``---`` は本文を截断する stray として扱う（見逃さない）。
    ``<details>`` 単独開き行（``<summary>`` が別行）と直前の空行は読み飛ばして次を見る。
    """
    while j < len(lines):
        s = lines[j].strip()
        if s == "":
            j += 1
            continue
        if _is_node_summary_line(lines[j]):
            return True   # ⬡ バッジ付き summary に到達 → 本物のノード開始
        if s.startswith("<details") and "<summary" not in s:
            j += 1
            continue      # <details> 単独開き → 次行の <summary> を確認
        return False      # バッジ無し（汎用 details / 平文 等）→ ノードではない
    return False


def _details_follows(lines: list[str], k: int) -> bool:
    """見出し行 ``lines[k]`` が**ノード見出し**か（後続に ⬡ バッジ付き ``<summary>`` が続くか）。

    続けば legit なノード分離（``--- 見出し <details>``）、続かなければ本文小見出し（截断被害）。
    ノード前置き（別見出し・blockquote・``**status**`` 等の bold 行・yaml フェンス・``</details>``）は
    読み飛ばす。平文 prose か 次の bare ``---`` か EOF に当たれば「ノードは続かない」＝本文小見出し。
    ``<details>``/``<summary>`` に到達したら ⬡ バッジの有無まで確認する（バッジ無しは本文）。
    """
    j = k + 1
    while j < len(lines):
        s = lines[j].strip()
        if s == "":
            j += 1
            continue
        if "<summary" in s or s.startswith("<details"):
            return _node_summary_starts(lines, j)  # ⬡ バッジ付きか確認して確定
        if s == "---":
            return False  # 次分離子まで <details> 無し → 本文小見出し
        if (_HEADING.match(s) or s.startswith(">") or s.startswith("**")
                or s.startswith("```") or s == "</details>"):
            j += 1
            continue      # ノード前置き候補 → さらに先を見る
        return False      # 平文 prose → 本文
    return False


def _nearest_node_id(lines: list[str], idx: int) -> str:
    """``idx`` 行より上で直近のノード summary の ID を返す（無ければ ``(file)``）。

    截断されるのは「その ``---`` の直前にある（＝直近上方の）ノードの本文」なので、
    截断被害を受けるノードを Finding の主体として指す。
    """
    for i in range(idx - 1, -1, -1):
        if _is_node_summary_line(lines[i]):
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
            # (1) 次ノード開始（⬡ バッジ付き summary が続く）→ 正常
            if _node_summary_starts(lines, j):
                continue
            # (2) inter-node の blockquote 注記 → 正常
            if nx.startswith(">"):
                continue
            # (3) 見出し: ノード見出し（⬡ バッジ付き summary が続く）なら正常、本文小見出しなら截断
            if _HEADING.match(nx) and _details_follows(lines, j):
                continue
            nid = _nearest_node_id(lines, i)
            out.append(Finding(
                nid, "warning", "stray-hr-in-body",
                "本文中の孤立 '---'（ノード分離記法の本文内誤用）がノード本文を截断する",
                rel, i + 1))
    return out
