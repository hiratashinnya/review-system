from __future__ import annotations

from .schema_types import DocSpec, Field, TableSpec
from .schema_values import (
    LEDGER, PROPOSAL, TRIAGE, LEDGER_ID_RE, PROPOSAL_ID_RE, TRIAGE_ID_RE,
    DECISION_POINTS, LEDGER_THEMES, DIVERGENCES, CONFIDENCES, TARGET_KINDS, ROUTINGS,
    PROPOSAL_STATUSES, VERDICTS, FINDING_ID_RE,
)
from .schema_version import LEDGER_SCHEMA_PREFIX
from .tomlwrite import DATE, INT, LINE, OPTDATE, STRLIST, TEXT

LEDGER_SPEC = DocSpec(
    kind=LEDGER,
    schema_const=LEDGER_SCHEMA_PREFIX,
    subdir="ledger",
    id_re=LEDGER_ID_RE,
    tables=(
        TableSpec("", (
            Field("schema", LINE),
            Field("id", LINE, pattern=LEDGER_ID_RE),
            Field("topic", LINE),
            Field("theme", LINE, enum=LEDGER_THEMES),
            Field("occurred_at", DATE),
            Field("decision_point", LINE, enum=DECISION_POINTS),
            Field("overridden_role", LINE),
            Field("divergence", LINE, enum=DIVERGENCES),
            Field("confidence_of_inference", LINE, enum=CONFIDENCES),
            Field("recorded_by", LINE),
            Field("affected_assets", STRLIST, path_ref=True),
            Field(
                "supersedes", LINE, required_nonempty=False, ref=LEDGER,
                pattern=LEDGER_ID_RE,
            ),
        )),
        TableSpec("source", (
            Field("issue", INT),
            Field("pr", INT, required_nonempty=False),
            Field("round", INT, required_nonempty=False),
            Field("finding_ids", STRLIST, required_nonempty=False,
                  pattern=FINDING_ID_RE),
        ), repeated=True, min_items=1),
        TableSpec("narrative", (
            Field("background", TEXT),
            Field("recommendation", TEXT),
            Field("recommendation_reason", TEXT),
            Field("uncertainty", TEXT, required_nonempty=False),
            Field("owner_verbatim", TEXT, lint="owner-verbatim"),
            Field("inferred_reason", TEXT, lint="inferred"),
        )),
    ),
)
