"""dispatch用の実体・commitを備えたroot/leaf artifact集合。"""
import hashlib
from issue_envelope.store import write
from issue_envelope.model import normalize
from tests.issue_envelope.fixtures import artifact
from tests.unit.codex_worktree_exec_support import git


def write_valid_plan_set(root, snapshot_oid, include_tests=False):
    documents, source_changes = {}, {}
    for kind, directory in (("VerificationDesign", "verification_design"),
                            ("ChangePlan", "change_plan")):
        data = artifact(kind)
        data.update(snapshot_oid=snapshot_oid, children=[data["id"] + "-tool"])
        if kind == "ChangePlan":
            data["work_units"].append(dict(id="WU-2", depends_on=[], scope=["tool"], ac_refs=["AC-1"]))
        if kind == "VerificationDesign":
            data["st_td"] = ["AC-1"]
        path = root / directory / f"{data['id']}.toml"
        write(path, data)
        leaf = artifact(kind, data["children"][0], parent=data["id"])
        leaf["snapshot_oid"] = snapshot_oid
        write(root / "tool" / directory / f"{data['id']}.toml", leaf)
        documents[kind] = (normalize(data), path)
    if include_tests:
        data = artifact("TestDesign")
        data["snapshot_oid"] = snapshot_oid
        plan, plan_path = documents["ChangePlan"]
        data.update(input_refs=[plan["id"]],
                    input_digest=hashlib.sha256(plan_path.read_bytes()).hexdigest())
        contents = {data["ut_td"][0]: b"# unit test design\n",
                    data["ut_tc"][0]: b"assert False, 'implementation missing'\n",
                    data["red_evidence"][0]["log"]: b"FAIL: implementation missing\n"}
        for name, content in contents.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            source_changes[name] = hashlib.sha256(content).hexdigest()
        for key in ("tc", "log"):
            evidence = data["red_evidence"][0]
            evidence[key + "_sha256"] = source_changes[evidence[key]]
        path = root / "test_design" / f"{data['id']}.toml"
        write(path, data)
        documents["TestDesign"] = (normalize(data), path)
    git(root, "add", "change_plan", "verification_design", "tool",
        *(["test_design", "tests"] if include_tests else []))
    git(root, "commit", "-qm", "valid phase artifacts")
    return documents, source_changes
