"""包含木と実行単位DAGを独立に検査する。"""


def dag_errors(items, label):
    errors, states = [], {}
    def visit(identifier):
        if states.get(identifier) == 1:
            errors.append(f"{label} が循環: {identifier}")
            return
        if states.get(identifier) == 2:
            return
        states[identifier] = 1
        for dependency in items[identifier]:
            if dependency not in items:
                errors.append(f"{label} 参照欠落: {dependency}")
            else:
                visit(dependency)
        states[identifier] = 2
    for identifier in items:
        visit(identifier)
    return errors


def tree_errors(records):
    errors = []
    groups = {}
    for data, _ in records:
        if data["artifact_type"] in ("ChangePlan", "VerificationDesign"):
            groups.setdefault((data["issue"], data["artifact_type"]), []).append(data)
    for key, nodes in groups.items():
        by_id = {node["id"]: node for node in nodes}
        roots = [node for node in nodes if not node["parent"]]
        if len(roots) != 1:
            errors.append(f"包含木のルートは1つ: {key}")
        if roots and not roots[0]["children"]:
            errors.append(f"単一対象でもrootとleafが必須: {key}")
        for node in nodes:
            identifier = node["id"]
            if len(node["children"]) != len(set(node["children"])):
                errors.append(f"子が重複: {identifier}")
            for child in node["children"]:
                if child not in by_id or by_id[child]["parent"] != identifier:
                    errors.append(f"parent/children不整合: {identifier}/{child}")
            parent = node["parent"]
            if parent and (parent not in by_id or identifier not in by_id[parent]["children"]):
                errors.append(f"parent/children不整合: {identifier}")
            if parent in by_id and not set(node["scope"]) <= set(by_id[parent]["scope"]):
                errors.append(f"子scopeが親scope外: {identifier}")
        errors.extend(dag_errors({n["id"]: n["children"] for n in nodes}, "包含木"))
        errors.extend(dag_errors({n["id"]: n["depends_on"] for n in nodes}, "ノード依存DAG"))
    return errors
