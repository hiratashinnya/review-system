"""Vocabulary and identifier patterns shared by document schemas."""

from __future__ import annotations

import re
import unicodedata

# --- 語彙（enum） -----------------------------------------------------------

DECISION_POINTS = (
    "triage-order", "scope-split", "implementation", "review-finding",
    "disposition", "merge", "schedule", "other",
)
LEDGER_THEMES = (
    "目的・評価", "開発工程", "実行体制", "品質原則", "検証・追跡", "AI判定", "記録管理",
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

SLUG_CHAR = r"""[^-\s/\\:*?"<>|`'()\[\]{}（）「」【】〔〕]"""
SLUG = rf"{SLUG_CHAR}+(?:-{SLUG_CHAR}+)*"
ASCII_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
LEDGER_ID_RE = re.compile(rf"^FBK-(?P<date>[0-9]{{8}})-(?P<slug>{SLUG})$")
PROPOSAL_ID_RE = re.compile(rf"^FBP-(?P<date>[0-9]{{8}})-(?P<slug>{ASCII_SLUG})$")
TRIAGE_ID_RE = re.compile(r"^TRG-(?P<year>\d{4})-W(?P<week>\d{2})$")
FINDING_ID_RE = re.compile(r"^F-\d+-\d+$")


def has_unsafe_ledger_slug_character(value: str) -> bool:
    """Reject Unicode control, format, surrogate, private-use, and unassigned chars."""
    return any(unicodedata.category(char).startswith("C") for char in value)

LEDGER = "ledger"
PROPOSAL = "proposal"
TRIAGE = "triage"
