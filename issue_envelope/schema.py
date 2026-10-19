"""共通Field宣言を利用する工程artifactスキーマ。"""
import re
from feedback_ledger.schema_types import DocSpec, Field, TableSpec
from feedback_ledger.tomlwrite import INT, LINE, STRLIST, TEXT

CONTRACTS = {
    "InvestigationReport": ("issue-investigator", "investigation", "IR"),
    "VerificationDesign": ("ac-designer", "verification_design", "VD"),
    "ChangePlan": ("change-planner", "solution_planning", "CP"),
    "TestDesign": ("test-writer", "test_design", "TD"),
}
COMMON = (
    Field("schema", LINE), Field("schema_version", INT), Field("id", LINE),
    Field("producer", LINE), Field("phase", LINE), Field("artifact_type", LINE),
    Field("issue", INT), Field("run_id", LINE), Field("target_key", LINE),
    Field("input_refs", STRLIST, False, ref="artifact"), Field("input_digest", LINE),
    Field("snapshot_oid", LINE), Field("status", LINE, enum=("ready", "stop")),
    Field("verification", STRLIST, False), Field("unresolved_findings", STRLIST, False),
    Field("owner_decisions", STRLIST, False, ref="ledger"),
    Field("unresolved_owner_decisions", STRLIST, False),
    Field("next_expected_artifact", LINE, False), Field("stop_reason", TEXT, False),
)
TREE = (
    Field("scope", STRLIST), Field("parent", LINE, False, ref="containment"),
    Field("children", STRLIST, False, ref="containment"),
    Field("depends_on", STRLIST, False, ref="dependency"),
)
DETAILS = {
    "InvestigationReport": tuple(Field(k, TEXT) for k in (
        "facts", "evidence", "current_behavior", "root_cause_or_unknown",
        "affected_surfaces", "constraints", "open_questions")) + (
            Field("investigation_required", INT, False), Field("investigation_reason", TEXT)),
    "VerificationDesign": tuple(Field(k, STRLIST, False) for k in (
        "st_td", "st_tc", "it_td", "it_tc")),
    "ChangePlan": tuple(Field(k, TEXT) for k in (
        "selected_solution", "interfaces", "invariants", "failure_behavior", "oos",
        "operational_verification")) + (Field("adr_refs", STRLIST, False, ref="adr"),),
    "TestDesign": (Field("work_unit", LINE), Field("ut_td", STRLIST, path_ref=True),
                   Field("ut_tc", STRLIST, path_ref=True)),
}
WORK_UNITS = TableSpec("work_units", (
    Field("id", LINE), Field("depends_on", STRLIST, False),
    Field("scope", STRLIST), Field("ac_refs", STRLIST),
), True, 1)

RED_EVIDENCE = TableSpec("red_evidence", (
    Field("tc", LINE, path_ref=True), Field("tc_sha256", LINE),
    Field("log", LINE, path_ref=True), Field("log_sha256", LINE),
    Field("command", LINE), Field("exit_code", INT),
    Field("failure_reason", LINE, enum=("implementation_missing",)),
), True, 1)


def make_spec(kind):
    tree = TREE if kind in ("ChangePlan", "VerificationDesign") else ()
    tables = (TableSpec("", COMMON + tree + DETAILS[kind]),)
    if kind == "ChangePlan":
        tables += (WORK_UNITS,)
    if kind == "TestDesign":
        tables += (RED_EVIDENCE,)
    prefix = CONTRACTS[kind][2]
    return DocSpec(kind, "issue-envelope/v1.0", "",
                   re.compile(rf"^{prefix}-[0-9]+(?:-[^/\\]+)?$"), tables)


SPECS = {kind: make_spec(kind) for kind in CONTRACTS}
CHANGE_PLAN_SPEC = SPECS["ChangePlan"]
VERIFICATION_DESIGN_SPEC = SPECS["VerificationDesign"]
