"""書込前の ADR 参照整合性。"""
from dsv2.query import deps
from harness_trace import adapt_document
from .index import index
from .schema import ADR_SPEC


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
