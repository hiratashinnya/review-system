"""ブロックから記録への変換。移設した設計理由は .ai/rationale/karte-module-split.md を参照。"""

from __future__ import annotations

import re

from .attempt_record import Attempt, Result
from .block_fields import optional_enum as _optional_enum, require_enum as _require_enum
from .block_fields import require_int_list as _require_int_list, require_nonempty as _require_nonempty
from .block_parser import Block
from .disposition import parse_disposition
from .field_validators import validate_finding_ids, validate_slug, validate_targets
from .finding_id import parse_finding_id
from .finding_record import Finding
from .format_error import KarteFormatError
from .int_args import matched_int, require_ascii_int
from .value_codec import check_list, normalize_locus
from .vocabulary import CHANGE_KINDS, DEFAULT_SCOPE, FINDING_STATUSES, HARM_LEVELS, OUTCOMES, SCOPES, SEVERITIES


def _finding_from_block(block: Block, issue: int) -> Finding:
    issue_of_id, _seq = parse_finding_id(block.title)
    if issue_of_id != issue:
        raise KarteFormatError(
            f"{block.lineno} 行目: finding ID の issue 番号が文書と食い違う: "
            f"{block.title}（文書は issue-{issue}）"
        )
    resolved_round = block.fields.get("resolved_round", "")
    resolved = None
    if isinstance(resolved_round, str) and resolved_round.strip():
        message = f"{block.lineno} 行目: resolved_round は整数: {resolved_round!r}"
        resolved = require_ascii_int(resolved_round.strip(), KarteFormatError(message))
    # ``scope`` は台帳側では任意（欠落は DEFAULT_SCOPE）。新規取り込み側で必須にしてある。
    disposition = parse_disposition(block)
    return Finding(
        id=block.title,
        status=_require_enum(block, "status", FINDING_STATUSES),
        harm=_require_enum(block, "harm", HARM_LEVELS),
        harm_detail=_require_nonempty(block, "harm_detail"),
        severity=_require_enum(block, "severity", SEVERITIES),
        locus=normalize_locus(block.fields.get("locus", "")),
        summary=_require_nonempty(block, "summary"),
        evidence=_require_nonempty(block, "evidence"),
        expected=_require_nonempty(block, "expected"),
        recheck=_require_nonempty(block, "recheck"),
        scope=_optional_enum(block, "scope", SCOPES, DEFAULT_SCOPE),
        disposition=disposition.kind,
        deferred_to=disposition.deferred_to,
        waived_by=disposition.waived_by,
        waived_reason=disposition.waived_reason,
        rounds=_require_int_list(block, "rounds"),
        resolved_round=resolved,
    )


def _attempt_from_block(block: Block, title: re.Match[str]) -> Attempt:
    number = matched_int(title.group(1), KarteFormatError, "Attempt 見出しの番号")
    rounds = _require_int_list(block, "round")
    if len(rounds) != 1:
        raise KarteFormatError(f"{block.lineno} 行目: 'round' は単一の整数: {block.title}")
    return Attempt(
        number=number,
        round=rounds[0],
        finding_ids=validate_finding_ids(block.fields.get("finding_ids", [])),
        root_cause=validate_slug(_require_nonempty(block, "root_cause"), "root_cause"),
        change_kind=_require_enum(block, "change_kind", CHANGE_KINDS),
        targets=validate_targets(block.fields.get("targets", [])),
        diagnosis=str(block.fields.get("diagnosis", "")).strip(),
    )


def _result_from_block(block: Block, title: re.Match[str]) -> Result:
    attempt_numbers = _require_int_list(block, "attempt")
    if len(attempt_numbers) != 1:
        raise KarteFormatError(f"{block.lineno} 行目: 'attempt' は単一の整数: {block.title}")
    declared = matched_int(title.group(1), KarteFormatError, "Result 見出しの番号")
    if attempt_numbers[0] != declared:
        raise KarteFormatError(
            f"{block.lineno} 行目: 見出し 'Result {declared}' と 'attempt: "
            f"{attempt_numbers[0]}' が食い違う"
        )
    return Result(
        attempt=declared,
        finding_ids=validate_finding_ids(block.fields.get("finding_ids", [])),
        touched=check_list(block.fields.get("touched", []), "touched"),
        outcome=_require_enum(block, "outcome", OUTCOMES),
        note=str(block.fields.get("note", "")).strip(),
    )
