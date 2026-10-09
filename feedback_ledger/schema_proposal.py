from __future__ import annotations

from .schema_types import DocSpec, Field, TableSpec
from .schema_values import (
    LEDGER, PROPOSAL, TRIAGE, LEDGER_ID_RE, PROPOSAL_ID_RE, TRIAGE_ID_RE,
    DECISION_POINTS, DIVERGENCES, CONFIDENCES, TARGET_KINDS, ROUTINGS,
    PROPOSAL_STATUSES, VERDICTS, FINDING_ID_RE,
)
from .tomlwrite import DATE, INT, LINE, OPTDATE, STRLIST, TEXT

PROPOSAL_SPEC = DocSpec(
    kind=PROPOSAL,
    schema_const="feedback-proposal/v1",
    subdir="queue",
    id_re=PROPOSAL_ID_RE,
    tables=(
        TableSpec("", (
            Field("schema", LINE),
            Field("id", LINE, pattern=PROPOSAL_ID_RE),
            Field("derived_from", STRLIST, ref=LEDGER, pattern=LEDGER_ID_RE),
            Field("target_assets", STRLIST, path_ref=True),
            Field("target_kind", LINE, enum=TARGET_KINDS),
            Field("routing", LINE, enum=ROUTINGS),
            Field("status", LINE, enum=PROPOSAL_STATUSES),
            Field("proposed_at", DATE),
            Field("decided_in", LINE, required_nonempty=False, ref=TRIAGE),
            Field("decided_by", LINE, required_nonempty=False),
            Field("decided_at", OPTDATE, required_nonempty=False),
            Field("decision_reason", LINE, required_nonempty=False),
            Field("issue_ref", LINE, required_nonempty=False),
            Field("applied_pr", INT, required_nonempty=False),
        )),
        TableSpec("body", (
            Field("problem", TEXT),
            Field("proposed_change", TEXT),
            Field("rationale", TEXT),
        )),
    ),
)
