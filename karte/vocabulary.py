"""カルテ書式の語彙（列挙値・セクション名・書式正規表現）。

各定義の設計理由は ``.ai/rationale/karte-module-split.md``「karte/vocabulary.py」を参照。
"""

import re

CHANGE_KINDS = ("logic", "data-structure", "interface", "config", "test", "doc", "revert")
HARM_LEVELS = ("real", "none")
SEVERITIES = ("blocker", "major", "minor")
FINDING_STATUSES = ("open", "resolved")
OUTCOMES = ("fixed", "partial", "no-change", "regressed")

SCOPES = ("in", "out")
DEFAULT_SCOPE = "in"

DISPOSITIONS = ("fix-here", "deferred", "waived")
CLEARING_DISPOSITIONS = ("deferred", "waived")
CLEARING_HARM = "real"

NEW_FINDING_TITLES = ("new", "NEW", "new-finding")

SECTION_FINDINGS = "Findings"
SECTION_ATTEMPTS = "Attempts"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*\Z")
FINDING_ID_RE = re.compile(r"^F-([1-9][0-9]*)-([0-9]{2,})\Z")
DOC_HEADER_RE = re.compile(r"^#\s+Karte:\s+issue-([1-9][0-9]*)\s*$")
ATTEMPT_TITLE_RE = re.compile(r"^Attempt\s+([1-9][0-9]*)\Z")
RESULT_TITLE_RE = re.compile(r"^Result\s+([1-9][0-9]*)\Z")
KEY_RE = re.compile(r"^([a-z][a-z0-9_]*):(.*)$")
DEFERRED_TO_RE = re.compile(r"^(?:#?[1-9][0-9]*|https?://[^\s]+/issues/[1-9][0-9]*)\Z")

FORBIDDEN_VALUE_CHARS = ("\n", "\r", "\0")
FORBIDDEN_LIST_ITEM_CHARS = (",", "[", "]")

FORMAT_VERSION = 1
