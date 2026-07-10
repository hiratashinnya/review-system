"""v2 コーパスの索引化: ``nodes/**/*.yaml`` を走査し ``meta.json`` を生成/読込する。

各ノードは path から ``stage/type/status`` を、サイドカー（``docidx.nodeyaml.parse`` で読む）から
``title/version/condition?/labels/scheduled/result?/log_ref?/carrier?/body_ref.file?/body_ref.anchor?/
source.*?/test.*?/edges``
を、ファイル stem から ``id`` を集約する。本文は型別 ``BODY_POLICY`` に従い、同名 ``.md``・
``body_ref.file``・本文なしを表す（``suppress``/``suppress_reason`` は issue #118 で機構ごと廃止）。
生成物 meta.json は手編集せず、``index`` で再生成する（FORMAT.md）。

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


class MetaError(ValueError):
    """path が config.yml の layout / status_dirs に反する不正配置。"""


# config.yml layout / status_dirs を正本とし一致させて直書き（配線は Sub-E で config 直読へ）。
LAYOUT = {
    "01-why": {"val", "sr"},
    "02-what": {"fr", "nfr", "spec"},
    "03-analysis": {"actor", "i", "o", "d", "p", "e", "term"},
    "05-design": {"orc", "ds", "mod", "dm", "port", "prs", "scm", "cfg", "prompt"},
    "04-verification": {"td", "tc", "tr", "verify", "fnd", "dd", "q", "pend"},
    "06-implementation": {"src"},
}
STAGES = set(LAYOUT)
# lifecycle を持つ型のみ status サブディレクトリ（config.yml status_dirs と一致・pend は #81 で追加）。
STATUS_DIRS = {
    "fnd": {"open", "resolved"},
    "q": {"open", "decided", "deferred", "closed"},
    "dd": {"decided", "closed"},
    "pend": {"open", "resolved", "deferred"},
}
BODY_POLICY = {
    "required": {
        "val", "sr", "fr", "nfr", "spec",
        "actor", "i", "o", "d", "p", "e", "term",
        "orc", "ds", "mod", "dm", "port", "prs", "scm", "cfg", "prompt",
        "tr", "verify", "fnd", "dd", "q", "pend",
    },
    "shared": {"td"},
    "none": {"tc", "src"},
}


def body_policy_for(typ: str) -> str:
    """type に対応する本文ポリシー（required/shared/none）を返す。未知 type は required。"""
    for policy, types in BODY_POLICY.items():
        if typ in types:
            return policy
    return "required"


def _posix(p: Path) -> str:
    return str(p).replace("\\", "/")


def _resolve_body(root: Path, yaml_path: Path, typ: str, data: dict) -> tuple[str, str | None, str]:
    """(body_policy, body_path, body_anchor) を返す。

    shared 型は ``body_ref.file`` を優先し、既存互換として同名 .md も許可する。none 型も移行中の
    既存同名 .md は表示できるよう拾うが、本文が無くても正当なノードとして扱う。
    """
    policy = body_policy_for(typ)
    raw = str(data.get("body_ref.file", "") or "").strip()
    anchor = str(data.get("body_ref.anchor", "") or "")
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            root_rel = root / p
            y_rel = yaml_path.parent / p
            p = root_rel if root_rel.exists() else y_rel
        try:
            return policy, _posix(p.resolve().relative_to(root.resolve())), anchor
        except ValueError:
            return policy, _posix(p), anchor
    same_stem = yaml_path.with_suffix(".md")
    if same_stem.exists():
        return policy, _posix(same_stem.relative_to(root)), ""
    return policy, None, ""


def read_node(yaml_path: Path, root: Path) -> dict:
    """1 サイドカー（``.yaml``）と対の ``.md`` から meta.json のノード辞書を組み立てる。"""
    rel = yaml_path.relative_to(root)
    parts = rel.parts  # ("nodes", stage, type, [status], filename)
    middle = parts[1:-1]  # stage, type, [status]
    stage = middle[0] if len(middle) >= 1 else ""
    typ = middle[1] if len(middle) >= 2 else ""
    status = middle[2] if len(middle) >= 3 else None

    # 配置検証（FORMAT.md / config.yml layout・status_dirs）: 不正配置を silently 誤メタ化しない。
    if parts[0] != "nodes":
        raise MetaError(f"nodes/ 配下でない: {_posix(rel)}")
    if stage not in LAYOUT:
        raise MetaError(f"未知 stage: {stage!r}（{_posix(rel)}）")
    if typ not in LAYOUT[stage]:
        raise MetaError(f"stage {stage!r} に無い type: {typ!r}（{_posix(rel)}）")
    allowed = STATUS_DIRS.get(typ)
    if allowed is None and status is not None:
        raise MetaError(f"type {typ!r} は status ディレクトリを取らない: {status!r}（{_posix(rel)}）")
    if allowed is not None:
        if status is None:
            raise MetaError(f"type {typ!r} は status ディレクトリ必須（{sorted(allowed)}・{_posix(rel)}）")
        if status not in allowed:
            raise MetaError(f"type {typ!r} の未知 status: {status!r}（許容 {sorted(allowed)}・{_posix(rel)}）")
    if len(middle) > 3:
        raise MetaError(f"想定外の階層深さ: {_posix(rel)}")

    data = nodeyaml.parse(yaml_path.read_text(encoding="utf-8"))
    scheduled = data.get("scheduled")
    if not isinstance(scheduled, str) or not scheduled.strip():
        raise MetaError(f"scheduled は非空文字列必須（{_posix(rel)}）")
    edges: list[dict] = []
    for e in data.get("edges", []) or []:
        row = {"to": str(e.get("to", ""))}
        if e.get("ref_version"):
            row["ref_version"] = str(e["ref_version"])
        if e.get("note"):
            row["note"] = str(e["note"])
        edges.append(row)
    body_policy, body_path, body_anchor = _resolve_body(root, yaml_path, typ, data)

    node = {
        "id": yaml_path.stem,
        "stage": stage,
        "type": typ,
        "status": status,
        "title": str(data.get("title", "")),
        "version": str(data.get("version", "")),
        "labels": list(data.get("labels", []) or []),
        "scheduled": scheduled,
        "edges": edges,
        "yaml_path": _posix(rel),
        "body_policy": body_policy,
        "body_path": body_path,
        "body_anchor": body_anchor,
    }
    if data.get("condition"):
        node["condition"] = str(data["condition"])
    # #81 で正式化した任意フィールドを集約（存在時のみ・suppress/suppress_reason は #118 で廃止済み）。
    # result(TR)/log_ref(TR)/carrier は meta.json 完全性（viewer 等）に必要。
    for opt in ("result", "log_ref", "carrier"):
        if data.get(opt):
            node[opt] = str(data[opt])
    for group in ("source", "test"):
        grouped = {}
        for field in ("file", "qualname", "kind"):
            key = f"{group}.{field}"
            if data.get(key):
                grouped[field] = str(data[key])
        if grouped:
            node[group] = grouped
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
