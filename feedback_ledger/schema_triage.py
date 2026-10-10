from __future__ import annotations

from .schema_types import DocSpec, Field, TableSpec
from .schema_values import (
    LEDGER, PROPOSAL, TRIAGE, LEDGER_ID_RE, PROPOSAL_ID_RE, TRIAGE_ID_RE,
    DECISION_POINTS, DIVERGENCES, CONFIDENCES, TARGET_KINDS, ROUTINGS,
    PROPOSAL_STATUSES, VERDICTS, FINDING_ID_RE,
)
from .tomlwrite import DATE, INT, LINE, OPTDATE, STRLIST, TEXT

TRIAGE_SPEC = DocSpec(
    kind=TRIAGE,
    schema_const="feedback-triage/v1",
    subdir="triage",
    id_re=TRIAGE_ID_RE,
    tables=(
        TableSpec("", (
            Field("schema", LINE),
            Field("id", LINE, pattern=TRIAGE_ID_RE),
            Field("period_start", DATE),
            Field("period_end", DATE),
            Field("reviewed", STRLIST, required_nonempty=False, ref=LEDGER, pattern=LEDGER_ID_RE),
        )),
        TableSpec("outcomes", (
            Field("entry", LINE, ref=LEDGER, pattern=LEDGER_ID_RE),
            Field("verdict", LINE, enum=VERDICTS),
            Field("proposal", LINE, required_nonempty=False, ref=PROPOSAL),
            Field("merged_into", LINE, required_nonempty=False, ref=LEDGER, pattern=LEDGER_ID_RE),
            Field("reason", LINE, required_nonempty=False),
        ), repeated=True),
        TableSpec("summary", (
            Field("notes", TEXT, required_nonempty=False),
        )),
    ),
)
