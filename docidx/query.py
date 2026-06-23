"""NodeIndex 上の検索・グラフ走査（純関数）。"""

from __future__ import annotations

import fnmatch

from .model import Node, NodeIndex


def search(
    index: NodeIndex,
    *,
    node_type: str | None = None,
    label: str | None = None,
    id_glob: str | None = None,
    text: str | None = None,
) -> list[Node]:
    """型/ラベル/ID グロブ/キーワードの AND で絞り込む。"""
    type_lc = node_type.lower() if node_type else None
    text_lc = text.lower() if text else None
    out: list[Node] = []
    for node in index.nodes:
        if type_lc and node.type.lower() != type_lc:
            continue
        if label and label not in node.labels:
            continue
        if id_glob and not fnmatch.fnmatch(node.id, id_glob):
            continue
        if text_lc and text_lc not in (node.heading + "\n" + node.body).lower():
            continue
        out.append(node)
    return out


def _drift(index: NodeIndex, target_id: str, ref_version: str) -> bool | None:
    """辺の ref_version が参照先バッジ x.y と不一致なら True、一致で False。

    参照先がインデックスに存在しない場合は None（判定不能）。

    依存仕様: SPEC-9 v0.2.0（依存辺のドリフト＝RULE-004）・02-meta-schema.md §1（DD-8）。
      なお docidx はドリフトを情報提示するのみで、FND 起票・判定（RULE 発火）は行わない。
    """
    target = index.by_id.get(target_id)
    if target is None or not ref_version or not target.version:
        return None
    return ref_version != target.version


def deps(index: NodeIndex, node_id: str) -> list[dict]:
    """node の出辺（依存先）一覧＋ドリフト情報を返す。

    依存仕様: 04-notation.md §3（edge スキーマ）・SPEC-9 v0.2.0（ドリフト・情報提示のみ）。
    """
    node = index.by_id.get(node_id)
    if node is None:
        return []
    rows: list[dict] = []
    for edge in node.edges:
        target = index.by_id.get(edge.to)
        rows.append({
            "to": edge.to,
            "ref_version": edge.ref_version,
            "target_version": target.version if target else None,
            "exists": target is not None,
            "drift": _drift(index, edge.to, edge.ref_version),
            "note": edge.note,
        })
    return rows


def dependents(index: NodeIndex, node_id: str) -> list[dict]:
    """node への入辺（依存元）一覧を逆引き索引から返す。

    依存仕様: 04-notation.md §3（edge スキーマ）・SPEC-9 v0.2.0（ドリフト・情報提示のみ）。
    """
    rows: list[dict] = []
    for src_id in index.dependents.get(node_id, ()):  # noqa: B007
        src = index.by_id.get(src_id)
        if src is None:
            continue
        ref = next((e.ref_version for e in src.edges if e.to == node_id), "")
        rows.append({
            "from": src_id,
            "type": src.type,
            "heading": src.heading,
            "ref_version": ref,
            "drift": _drift(index, node_id, ref),
            "file": src.file,
            "line": src.line,
        })
    return rows
