"""CPの選択単位と2a/2bが消費するTestDesignを同じ入力へ束縛する。"""
import hashlib
import tomllib
from issue_envelope.model import normalize
from .committed_artifact import read_committed_artifact


def _selected_unit(plan, work_unit):
    if (not isinstance(work_unit, str) or not work_unit.strip()
            or len([unit for unit in plan["work_units"] if unit["id"] == work_unit]) != 1):
        raise ValueError("single approved work unit required")


def _read_design(reference, root, verified):
    if not isinstance(reference, dict) or set(reference) != {"artifact", "artifact_digest"}:
        raise ValueError("consumed TestDesign reference required")
    path = root / reference["artifact"]
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("consumed TestDesign outside worktree")
    content = read_committed_artifact(path, root)
    if hashlib.sha256(content).hexdigest() != reference["artifact_digest"]:
        raise ValueError("consumed TestDesign digest mismatch")
    design = normalize(tomllib.loads(content.decode("utf-8")))
    if design["artifact_type"] != "TestDesign" or verified.get(path.resolve()) != design["id"]:
        raise ValueError("consumed TestDesign outside verified repository collection")
    return design


def validate_work_unit_binding(binding, data, role, root, verified):
    expected = binding["expected"]
    if data["artifact_type"] == "TestDesign":
        plans = [path for path, identifier in verified.items() if identifier in data["input_refs"]]
        plans = [normalize(tomllib.loads(read_committed_artifact(path, root).decode("utf-8")))
                 for path in plans]
        plans = [plan for plan in plans if plan["artifact_type"] == "ChangePlan"]
        if len(plans) != 1:
            raise ValueError("TestDesign requires one approved input plan")
        plan = plans[0]
    elif role in {"test-writer", "issue-implementer", "pr-reviewer"}:
        plan = data
    else:
        return
    _selected_unit(plan, expected.get("work_unit"))
    if role == "test-writer":
        return
    design = data if data["artifact_type"] == "TestDesign" else _read_design(
        expected.get("test_design"), root, verified)
    plan_path = next(path for path, identifier in verified.items() if identifier == plan["id"])
    plan_digest = hashlib.sha256(read_committed_artifact(plan_path, root)).hexdigest()
    if (design["work_unit"] != expected["work_unit"]
            or design["input_refs"] != [plan["id"]] or design["input_digest"] != plan_digest
            or any(record[key] != expected[key] for record in (plan, design)
                   for key in ("issue", "run_id", "target_key", "snapshot_oid"))):
        raise ValueError("consumed TestDesign plan/work_unit mismatch")
