"""v2 コーパスの索引化: ``nodes/**/*.yaml`` を走査し ``meta.json`` を生成/読込する。

各ノードは path から ``stage/type/status`` を、サイドカー（``docidx.nodeyaml.parse`` で読む）から
``title/version/condition?/labels/scheduled/edges`` を、ファイル stem から ``id`` を、対の ``.md`` を
``body_path`` として集約する。生成物 meta.json は手編集せず、``index`` で再生成する（FORMAT.md）。

依存仕様: doc-system-v2/FORMAT.md（Sub-A・新フォーマット正本）・doc-system-v2/config.yml（layout /
  status_dirs / trace_scope）。サイドカー読取は docidx.nodeyaml（既存・再利用）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root（docidx 用）
from docidx import nodeyaml  # noqa: E402

DEFAULT_ROOT = "doc-system-v2"
META_FILENAME = "meta.json"

# config.yml layout / status_dirs を正本とし一致させて直書き（配線は Sub-E で config 直読へ）。
STAGES = {"01-why", "02-what", "03-analysis", "05-design", "04-verification"}
STATUS_DIRS = {
    "fnd": {"open", "resolved"},
    "q": {"open", "decided", "deferred", "closed"},
    "dd": {"decided", "closed"},
}


def _posix(p: Path) -> str:
    return str(p).replace("\\", "/")


def read_node(yaml_path: Path, root: Path) -> dict:
    """1 サイドカー（``.yaml``）と対の ``.md`` から meta.json のノード辞書を組み立てる。"""
    rel = yaml_path.relative_to(root)
    parts = rel.parts  # ("nodes", stage, type, [status], filename)
    middle = parts[1:-1]  # stage, type, [status]
    stage = middle[0] if len(middle) >= 1 else ""
    typ = middle[1] if len(middle) >= 2 else ""
    status = middle[2] if len(middle) >= 3 else None

    data = nodeyaml.parse(yaml_path.read_text(encoding="utf-8"))
    edges: list[dict] = []
    for e in data.get("edges", []) or []:
        row = {"to": str(e.get("to", ""))}
        if e.get("ref_version"):
            row["ref_version"] = str(e["ref_version"])
        if e.get("note"):
            row["note"] = str(e["note"])
        edges.append(row)

    node = {
        "id": yaml_path.stem,
        "stage": stage,
        "type": typ,
        "status": status,
        "title": str(data.get("title", "")),
        "version": str(data.get("version", "")),
        "labels": list(data.get("labels", []) or []),
        "scheduled": str(data.get("scheduled", "") or ""),
        "edges": edges,
        "yaml_path": _posix(rel),
        "body_path": _posix(rel.with_suffix(".md")),
    }
    if data.get("condition"):
        node["condition"] = str(data["condition"])
    return node


def scan_nodes(root: Path) -> list[dict]:
    """``<root>/nodes/**/*.yaml`` を走査してノード辞書のリスト（path ソート）を返す。"""
    nodes_dir = root / "nodes"
    if not nodes_dir.exists():
        return []
    return [read_node(y, root) for y in sorted(nodes_dir.rglob("*.yaml"))]


def build_meta(root: Path) -> dict:
    """メモリ上で meta 構造を組み立てる（ファイルには書かない）。"""
    return {"format": "doc-system-v2", "root": root.name, "nodes": scan_nodes(root)}


def write_meta(root: Path, out: Path) -> dict:
    """meta を生成して ``out`` へ書き込み、生成した dict を返す。"""
    meta = build_meta(root)
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def load_meta(root: Path, meta_path: Path | None) -> dict:
    """meta.json があれば読み、無ければディスク走査で構築する（照会用）。"""
    if meta_path and meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return build_meta(root)


def index_by_id(meta: dict) -> dict[str, dict]:
    """``id -> ノード辞書``（先勝ち）を返す。"""
    out: dict[str, dict] = {}
    for n in meta["nodes"]:
        out.setdefault(n["id"], n)
    return out


def duplicates(meta: dict) -> dict[str, list[str]]:
    """id 重複を ``id -> [yaml_path, ...]`` で返す（1件超のみ）。"""
    locs: dict[str, list[str]] = {}
    for n in meta["nodes"]:
        locs.setdefault(n["id"], []).append(n["yaml_path"])
    return {k: v for k, v in locs.items() if len(v) > 1}
