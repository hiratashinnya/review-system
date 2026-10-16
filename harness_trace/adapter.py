"""フィールド名に依存しない参照変換。"""


def adapt_document(spec, data, path):
    edges = []
    for _, (table, field) in spec.field_map().items():
        if not field.ref:
            continue
        sections = [data] if not table.name else data.get(table.name, [])
        if not table.repeated and table.name:
            sections = [sections]
        for section in sections:
            value = section.get(field.name, [])
            for target in value if isinstance(value, list) else [value]:
                if target:
                    edges.append({"to": target, "ref_version": "", "note": field.ref})
    return {"id": data["id"], "type": spec.kind, "edges": edges,
            "version": data.get("schema", ""), "yaml_path": str(path)}


def build_index(documents):
    nodes = [adapt_document(spec, data, path) for spec, data, path in documents]
    ids = [node["id"] for node in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("索引内で id が重複")
    return {"nodes": nodes}
