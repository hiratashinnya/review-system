"""3種の文書スキーマ（台帳エントリ／改訂案／週次棚卸し記録）の宣言。

ここが**キー集合・並び・型・語彙の唯一の正本**で、次の3つが同じ宣言を読む。

  * canonical シリアライザ（:mod:`feedback_ledger.tomlwrite`）— 並びを決める
  * 検証器（:mod:`feedback_ledger.model`）— L1（キー集合の完全一致・enum）を決める
  * 共有 schema の JSON（``.ai/schema/feedback-*-v1.json`` と
    ``tests/unit/test_feedback_ledger.py`` が対応を機械検査する）

**なぜ「欠落も未知も拒否する完全一致」なのか**（L1）:
  台帳は毎週人が読み、数年にわたって積み上がる。キーを任意にすると「ある年から欄が増えた／
  消えた」記録が混在し、機械集計も差分レビューも成立しなくなる。省略可能な値は **キーを消さず
  空値**（``""`` / ``0`` / ``[]``）で表す。

依存仕様: Issue #522「Scope / 文書スキーマ3種（TOML）」。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .tomlwrite import DATE, INT, LINE, OPTDATE, STRLIST, TEXT

# --- 語彙（enum） -----------------------------------------------------------

DECISION_POINTS = (
    "triage-order", "scope-split", "implementation", "review-finding",
    "disposition", "merge", "schedule", "other",
)
# `skill:<name>` だけは前方一致の拡張形（どの skill の推奨を曲げたかを残すため）。
OVERRIDDEN_ROLES = ("main-thread", "issue-implementer", "issue-fixer", "pr-reviewer")
OVERRIDDEN_ROLE_SKILL_RE = re.compile(r"^skill:[a-z0-9]+(?:-[a-z0-9]+)*$")
DIVERGENCES = ("reversal", "narrowing", "widening", "deferral", "alternative-means")
CONFIDENCES = ("low", "medium", "high")
TARGET_KINDS = ("contract", "criteria", "governance", "tooling")
ROUTINGS = ("issue", "node")
PROPOSAL_STATUSES = ("pending", "approved", "rejected", "applied", "superseded")
VERDICTS = ("proposed", "no-change", "merged-into", "need-more-evidence")

# --- id / ファイル名 ---------------------------------------------------------

SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
LEDGER_ID_RE = re.compile(rf"^FBK-(?P<date>\d{{8}})-(?P<slug>{SLUG})$")
PROPOSAL_ID_RE = re.compile(rf"^FBP-(?P<date>\d{{8}})-(?P<slug>{SLUG})$")
TRIAGE_ID_RE = re.compile(r"^TRG-(?P<year>\d{4})-W(?P<week>\d{2})$")
FINDING_ID_RE = re.compile(r"^F-\d+-\d+$")

LEDGER = "ledger"
PROPOSAL = "proposal"
TRIAGE = "triage"

# --- 宣言の型 ---------------------------------------------------------------


@dataclass(frozen=True)
class Field:
    """1つのキーの宣言。

    ``required_nonempty``
        空値（``""``/``[]``/``0``）を認めないか。認めない欄は「必ず書かれる」ことが
        台帳としての価値に直結するもの（誰が・いつ・何を曲げたか）に限る。
    ``lint``
        内容 lint の種別（``owner-verbatim``＝推測語彙の混入拒否＝L4／
        ``inferred``＝``推測：`` マーカー必須＋断定語彙の拒否＝L5）。
    ``ref``
        値が他文書の id を指す欄の種別（実在検査に使う）。
    """

    name: str
    kind: str
    required_nonempty: bool = True
    enum: tuple[str, ...] | None = None
    pattern: re.Pattern | None = None
    lint: str | None = None
    ref: str | None = None
    path_ref: bool = False


@dataclass(frozen=True)
class TableSpec:
    name: str  # "" はトップレベル
    fields: tuple[Field, ...]
    repeated: bool = False
    min_items: int = 0


@dataclass(frozen=True)
class DocSpec:
    kind: str
    schema_const: str
    subdir: str
    id_re: re.Pattern
    tables: tuple[TableSpec, ...]

    def field_map(self) -> dict[str, tuple[TableSpec, Field]]:
        return {
            f"{table.name}.{field.name}" if table.name else field.name: (table, field)
            for table in self.tables
            for field in table.fields
        }


LEDGER_SPEC = DocSpec(
    kind=LEDGER,
    schema_const="feedback-ledger/v1",
    subdir="ledger",
    id_re=LEDGER_ID_RE,
    tables=(
        TableSpec("", (
            Field("schema", LINE),
            Field("id", LINE, pattern=LEDGER_ID_RE),
            Field("topic", LINE),
            Field("occurred_at", DATE),
            Field("decision_point", LINE, enum=DECISION_POINTS),
            Field("overridden_role", LINE),
            Field("divergence", LINE, enum=DIVERGENCES),
            Field("confidence_of_inference", LINE, enum=CONFIDENCES),
            Field("recorded_by", LINE),
            Field("affected_assets", STRLIST, path_ref=True),
            Field("supersedes", LINE, required_nonempty=False, ref=LEDGER),
        )),
        TableSpec("source", (
            Field("issue", INT),
            Field("pr", INT, required_nonempty=False),
            Field("round", INT, required_nonempty=False),
            Field("finding_ids", STRLIST, required_nonempty=False,
                  pattern=FINDING_ID_RE),
        )),
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

PROPOSAL_SPEC = DocSpec(
    kind=PROPOSAL,
    schema_const="feedback-proposal/v1",
    subdir="queue",
    id_re=PROPOSAL_ID_RE,
    tables=(
        TableSpec("", (
            Field("schema", LINE),
            Field("id", LINE, pattern=PROPOSAL_ID_RE),
            Field("derived_from", STRLIST, ref=LEDGER),
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
            Field("reviewed", STRLIST, required_nonempty=False, ref=LEDGER),
        )),
        TableSpec("outcomes", (
            Field("entry", LINE, ref=LEDGER),
            Field("verdict", LINE, enum=VERDICTS),
            Field("proposal", LINE, required_nonempty=False, ref=PROPOSAL),
            Field("merged_into", LINE, required_nonempty=False, ref=LEDGER),
            Field("reason", LINE, required_nonempty=False),
        ), repeated=True),
        TableSpec("summary", (
            Field("notes", TEXT, required_nonempty=False),
        )),
    ),
)

SPECS = {LEDGER: LEDGER_SPEC, PROPOSAL: PROPOSAL_SPEC, TRIAGE: TRIAGE_SPEC}


def filename_for(spec: DocSpec, document_id: str) -> str:
    return f"{document_id}.toml"


def valid_overridden_role(value: str) -> bool:
    return value in OVERRIDDEN_ROLES or bool(OVERRIDDEN_ROLE_SKILL_RE.match(value))
