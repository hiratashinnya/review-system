"""repo全体の工程artifactをread-onlyで検査する。"""
from feedback_ledger.tomlwrite import dumps
from dsv2.query import deps
from .graph import dag_errors, tree_errors
from .coverage import coverage_errors
from .handoff import validate_handoff
from .query import index
from .schema import SPECS
from .store import load
from .path_binding import path_errors
from .red_evidence import red_errors


def check(repo, expectations=None):
    try:
        records = load(repo)
        meta = index(repo)
    except (ValueError, OSError) as exc:
        return [str(exc)]
    errors = tree_errors(records) + coverage_errors(records)
    for data, path in records:
        identifier = data["id"]
        errors.extend(path_errors(repo, data))
        errors.extend(red_errors(repo, data))
        if (data["status"] != "ready" or data["unresolved_findings"]
                or data["unresolved_owner_decisions"]):
            errors.append(f"STOP/未解消finding/未決owner decision: {identifier}")
        if path.read_text(encoding="utf-8") != dumps(SPECS[data["artifact_type"]], data):
            errors.append(f"canonical不一致: {path}")
        for edge in deps(meta, identifier):
            if not edge["exists"]:
                errors.append(f"参照欠落: {identifier} -> {edge['to']}")
        if data["artifact_type"] == "ChangePlan":
            units = data["work_units"]
            if len({u["id"] for u in units}) != len(units):
                errors.append(f"work unit重複: {identifier}")
            errors.extend(dag_errors({u["id"]: u["depends_on"] for u in units}, "work_units DAG"))
        if expectations and identifier in expectations:
            try:
                validate_handoff(data, expectations[identifier])
            except ValueError as exc:
                errors.append(f"{identifier}: {exc}")
    for identifier in set(expectations or {}) - {data["id"] for data, _ in records}:
        errors.append(f"期待artifact欠落: {identifier}")
    return errors
