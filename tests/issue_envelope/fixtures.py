"""宣言から全フィールドを揃えるartifact fixture。"""
from issue_envelope.schema import SPECS, CONTRACTS


def artifact(kind="VerificationDesign", identifier=None, parent="", children=()):
    spec = SPECS[kind]
    raw = {field.name: ([] if field.kind == "strlist" else "記録")
           for table in spec.tables if not table.name for field in table.fields}
    for table in spec.tables:
        for field in table.fields:
            if not table.name and field.kind == "strlist":
                raw[field.name] = []
    raw.update(schema=spec.schema_const, schema_version=1, issue=371,
               id=identifier or f"{CONTRACTS[kind][2]}-371",
               producer=CONTRACTS[kind][0], phase=CONTRACTS[kind][1],
               artifact_type=kind, run_id="run-1", target_key="issue-371",
               input_refs=[], input_digest="a" * 64, snapshot_oid="b" * 40,
               status="ready", verification=[], unresolved_findings=[],
               owner_decisions=[], unresolved_owner_decisions=[],
               next_expected_artifact="", stop_reason="")
    if kind in ("ChangePlan", "VerificationDesign"):
        raw.update(scope=["tool"], parent=parent, children=list(children), depends_on=[])
    if kind == "VerificationDesign":
        raw.update(st_td=["ST-TD-1"] if not parent else [],
                   st_tc=["ST-TC-1"] if not parent else [], it_td=[], it_tc=[])
    if kind == "ChangePlan":
        raw.update(adr_refs=[], work_units=[dict(id="WU-1", depends_on=[],
                                               scope=["tool"], ac_refs=["AC-1"])])
    if kind == "TestDesign":
        raw.update(ut_td=["UT-TD-1"], ut_tc=["tests/tool/test_unit.py"])
    if kind == "InvestigationReport":
        raw.update(investigation_required=1, investigation_reason="原因不明")
    return raw
