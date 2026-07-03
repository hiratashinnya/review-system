"""meta.json 上のグラフ照会（純関数）: deps / dependents / orphans / drift。

RULE-004（ドリフト）は「辺の ``ref_version``（x.y）≠ 参照先サイドカー ``version`` の x.y」。z は
伝播不問（DD-8）。参照元ノードが ``suppress: [RULE-004]`` を持つ辺は drift 判定を凍結免除する
（RULE-004 は always_error＝RULE-005/007 でないため suppress 可能・#81 で正式化・DD-2）。
孤立（orphans）は in/out 辺がともに 0 本のノード（RULE-005＝always_error なので suppress 無視で正）。

依存仕様: doc-system-v2/config.yml（RULE-004 / always_error / trace_scope）・FORMAT.md（無名依存辺・親子も edge）。
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


def _suppresses_drift(node: dict) -> bool:
    """参照元ノードが RULE-004（ドリフト）を suppress で凍結免除しているか。

    RULE-004 は always_error（RULE-005/007）ではないため suppress 可能（#81 で正式化・DD-2 の
    「過去の検証事実スナップショット＝版上げドリフト凍結免除」等）。抑制辺は drift から除外する。
    """
    return "RULE-004" in (node.get("suppress") or [])


def deps(meta: dict, node_id: str) -> list[dict] | None:
    """node の出辺（依存先）＋存在/ドリフト情報。node が無ければ None。"""
    by_id = index_by_id(meta)
    node = by_id.get(node_id)
    if node is None:
        return None
    suppressed = _suppresses_drift(node)  # RULE-004 抑制ノードはドリフト判定を凍結免除
    rows: list[dict] = []
    for e in node["edges"]:
        target = by_id.get(e["to"])
        ref = e.get("ref_version", "")
        rows.append({
            "to": e["to"],
            "ref_version": ref,
            "exists": target is not None,
            "target_version": target["version"] if target else None,
            "drift": None if suppressed else _drift(ref, target),
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
                "drift": None if _suppresses_drift(src) else _drift(ref, node),
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


def slug_collisions(meta: dict, slugs: list[str]) -> dict[str, str]:
    """著作 slug 群がコーパス既存 id と衝突するか／slug 群内で重複するかを返す（fail-close 用）。

    id = slug = ファイル名 stem はグローバル一意（FORMAT.md §slug）。この一意性は slugify.py でも
    validate.py（per-node）でも担保できない＝コーパス横断の照合が必要。reconciliation-validator が
    書込前に本関数（dsv2 check-slug 経由）で fail-close 判定する（DD-22・Sub-D・issue #73）。

    戻り値: ``{slug: reason}``（衝突分のみ）。reason は
      * ``"corpus:<yaml_path>"`` … 既存コーパスノードと id 衝突。
      * ``"batch(xN)"``          … 今回の著作 slug 群内で N 回重複。
    衝突が無ければ空 dict（＝一意で書込可）。

    依存仕様: doc-system-v2/FORMAT.md（§slug グローバル一意）・config.yml（id=stem）。
    """
    by_id = index_by_id(meta)
    counts: dict[str, int] = {}
    for s in slugs:
        counts[s] = counts.get(s, 0) + 1
    out: dict[str, str] = {}
    for s, n in counts.items():
        if s in by_id:
            out[s] = f"corpus:{by_id[s]['yaml_path']}"
        elif n > 1:
            out[s] = f"batch(x{n})"
    return out


def drift(meta: dict) -> list[dict]:
    """全辺を走査し、ref_version が参照先バッジ x.y とドリフトしている辺を列挙（RULE-004）。"""
    by_id = index_by_id(meta)
    out: list[dict] = []
    for src in meta["nodes"]:
        if _suppresses_drift(src):
            continue  # RULE-004 抑制ノードの辺はドリフト列挙から除外（#81・DD-2）
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
