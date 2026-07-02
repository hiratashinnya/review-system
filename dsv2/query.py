"""meta.json 上のグラフ照会（純関数）: deps / dependents / orphans / drift。

RULE-004（ドリフト）は「辺の ``ref_version``（x.y）≠ 参照先サイドカー ``version`` の x.y」。z は
伝播不問（DD-8）。孤立（orphans）は in/out 辺がともに 0 本のノード。

依存仕様: doc-system-v2/config.yml（RULE-004 / trace_scope）・FORMAT.md（無名依存辺・親子も edge）。
"""

from __future__ import annotations

from .meta import index_by_id


def _xy(version: str) -> str:
    """``x.y.z``（または ``x.y``）から比較単位 ``x.y`` を返す。"""
    parts = version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else version


def _drift(ref_version: str, target: dict | None) -> bool | None:
    """辺 ref_version（x.y）が参照先バッジ x.y と不一致なら True。判定不能なら None。"""
    if not ref_version or target is None or not target.get("version"):
        return None
    return _xy(ref_version) != _xy(target["version"])


def deps(meta: dict, node_id: str) -> list[dict] | None:
    """node の出辺（依存先）＋存在/ドリフト情報。node が無ければ None。"""
    by_id = index_by_id(meta)
    node = by_id.get(node_id)
    if node is None:
        return None
    rows: list[dict] = []
    for e in node["edges"]:
        target = by_id.get(e["to"])
        ref = e.get("ref_version", "")
        rows.append({
            "to": e["to"],
            "ref_version": ref,
            "exists": target is not None,
            "target_version": target["version"] if target else None,
            "drift": _drift(ref, target),
            "note": e.get("note", ""),
        })
    return rows


def dependents(meta: dict, node_id: str) -> list[dict]:
    """node への入辺（依存元）一覧を全ノード走査で逆引きする。"""
    rows: list[dict] = []
    by_id = index_by_id(meta)
    node = by_id.get(node_id)
    for src in meta["nodes"]:
        for e in src["edges"]:
            if e["to"] != node_id:
                continue
            ref = e.get("ref_version", "")
            rows.append({
                "from": src["id"],
                "type": src["type"],
                "ref_version": ref,
                "drift": _drift(ref, node),
                "yaml_path": src["yaml_path"],
            })
    return rows


def orphans(meta: dict) -> list[dict]:
    """in/out 辺がともに 0 本の完全孤立ノード（RULE-005 相当）。"""
    referenced: set[str] = set()
    for n in meta["nodes"]:
        for e in n["edges"]:
            referenced.add(e["to"])
    return [n for n in meta["nodes"] if not n["edges"] and n["id"] not in referenced]


def drift(meta: dict) -> list[dict]:
    """全辺を走査し、ref_version が参照先バッジ x.y とドリフトしている辺を列挙（RULE-004）。"""
    by_id = index_by_id(meta)
    out: list[dict] = []
    for src in meta["nodes"]:
        for e in src["edges"]:
            ref = e.get("ref_version", "")
            target = by_id.get(e["to"])
            if _drift(ref, target) is True:
                out.append({
                    "from": src["id"],
                    "to": e["to"],
                    "ref_version": ref,
                    "target_version": target["version"],
                })
    return out
