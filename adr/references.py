"""書込前の ADR 参照整合性。"""
from dsv2.query import deps
from harness_trace import adapt_document
from pathlib import Path
from .index import index
from .schema import ADR_SPEC


def validate_assets(data, repo):
    directory = Path(repo).resolve()
    for asset in data["affected_assets"]:
        target = (directory / asset).resolve()
        if not target.is_relative_to(directory) or not target.exists():
            raise ValueError(f"資産がrepo内に存在しない: {asset}")


def validate_references(data, root, repo):
    meta = index(root, repo)
    meta["nodes"] = [node for node in meta["nodes"] if node["id"] != data["id"]]
    meta["nodes"].append(adapt_document(ADR_SPEC, data, "draft"))
    for edge in deps(meta, data["id"]):
        if not edge["exists"]:
            raise ValueError(f"参照が存在しない: {edge['to']}")
    if data["supersedes"] == data["id"]:
        raise ValueError("自分自身を supersedes できない")
    by_id = {node["id"]: node for node in meta["nodes"]}
    if any(edge["to"] == data["id"] for node in by_id.values()
           for edge in node["edges"] if edge.get("note") == "adr"):
        raise ValueError("supersedes が循環しうる既存参照")
