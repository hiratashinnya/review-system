"""ADR v1.0 の宣言。逐語は台帳へ置き、参照だけを保持する。"""
import re
from feedback_ledger.schema_types import DocSpec, Field, TableSpec
from feedback_ledger.schema_values import LEDGER_ID_RE, SLUG
from feedback_ledger.tomlwrite import DATE, INT, LINE, STRLIST, TEXT

ADR_ID_RE = re.compile(rf"^ADR-(?P<date>[0-9]{{8}})-(?P<slug>{SLUG})$")
ADR_SPEC = DocSpec("adr", "harness-adr/v1.0", "", ADR_ID_RE, (
    TableSpec("", (
        Field("schema", LINE), Field("id", LINE, pattern=ADR_ID_RE),
        Field("topic", LINE), Field("decided_at", DATE), Field("phase", LINE),
        Field("recorded_by", LINE), Field("affected_assets", STRLIST, path_ref=True),
        Field("supersedes", LINE, False, pattern=ADR_ID_RE, ref="adr"),
        Field("owner_decision_refs", STRLIST, False, pattern=LEDGER_ID_RE, ref="ledger"),
    )),
    TableSpec("source", (Field("issue", INT), Field("pr", INT, False)), True, 1),
    TableSpec("context", (Field("problem", TEXT), Field("constraints", TEXT, False))),
    TableSpec("decision", (
        Field("chosen", TEXT), Field("rationale", TEXT),
        Field("tracking_status", LINE, enum=("pending", "filed", "not_needed")),
        Field("tracking_issue", INT, False), Field("no_tracking_reason", TEXT, False),
    )),
    TableSpec("alternatives", (Field("option", TEXT), Field("rejection_reason", TEXT)), True, 1),
    TableSpec("consequences", (
        Field("positive", TEXT, False), Field("negative", TEXT, False),
        Field("followups", TEXT, False),
    )),
))
