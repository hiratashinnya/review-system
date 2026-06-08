"""基準フロントマターの lint（S5 検証器）。design/05・13 S5・DD7。

パーサが読めた dict を、値レベルで検証する：必須キー・override/severity/determinism の語彙・
id 一意性・version の MAJOR 対応・extends 先の存在。失敗は O-14 同形式（reason＋subject）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

# version は MAJOR.MINOR(.PATCH…) のドット形式のみ（各成分が数字）＝M2
_VERSION = re.compile(r"(\d+)(?:\.\d+)+")

# 対応する MAJOR（コメントでなく定数＝reviewer version / lint / 版スタンプの単一ソース・DD7）
SUPPORTED_CRITERIA_MAJOR: frozenset[int] = frozenset({1})
SUPPORTED_POLICY_MAJOR: frozenset[int] = frozenset({1})

_OVERRIDE = {"locked", "tighten-only", "open"}
_SEVERITY = {"error", "warning", "info"}
_DETERMINISM = {"deterministic", "tradeoff", "judgment"}
_REQUIRED = ("doc_type", "scope", "rules")


@dataclass(frozen=True, slots=True)
class LintError:
    reason: str
    subject: str | None = None


@dataclass(frozen=True, slots=True)
class CriteriaLintResult:
    errors: tuple[LintError, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def major_of(version: object) -> int | None:
    """`"MAJOR.MINOR"` 文字列から MAJOR(int) を取り出す（DD7）。

    MAJOR.MINOR の**ドット形式（各成分が数字）以外は受理しない**（M2）。
    例：`"1.0"`→1、`"1"`/`"1."`/`"x.y"`→None（lint で fail-close）。
    """
    if not isinstance(version, str):
        return None
    m = _VERSION.fullmatch(version.strip())
    return int(m.group(1)) if m else None


def lint_criteria(parsed: dict, *, exists: Callable[[str], bool]) -> CriteriaLintResult:
    """基準フロントマター dict を検証し、CriteriaLintResult を返す。"""
    errors: list[LintError] = []

    for key in _REQUIRED:
        if key not in parsed:
            errors.append(LintError(f"必須キーが無い: {key}"))

    version = parsed.get("version")
    if version is not None:
        major = major_of(version)
        if major is None:
            errors.append(LintError(f"version は \"MAJOR.MINOR\" 文字列: {version!r}"))
        elif major not in SUPPORTED_CRITERIA_MAJOR:
            errors.append(LintError(
                f"未対応の基準 MAJOR={major}（対応={sorted(SUPPORTED_CRITERIA_MAJOR)}）", str(version)))

    extends = parsed.get("extends")
    if extends not in (None, ""):
        if not exists(str(extends)):
            errors.append(LintError("extends 先が存在しない（継承リンク切れ）", str(extends)))

    rules = parsed.get("rules")
    if rules is not None and not isinstance(rules, list):
        errors.append(LintError("rules はブロック列であるべき"))
        rules = []

    seen: set[str] = set()
    for idx, rule in enumerate(rules or []):
        if not isinstance(rule, dict):
            errors.append(LintError(f"rules[{idx}] はマッピングであるべき"))
            continue
        rid = rule.get("id")
        if not rid:
            errors.append(LintError(f"rules[{idx}] に id が無い"))
        else:
            if rid in seen:
                errors.append(LintError(f"rule id が重複: {rid}", str(rid)))
            seen.add(rid)
        _check_enum(rule, "override", _OVERRIDE, errors, rid)
        _check_enum(rule, "severity", _SEVERITY, errors, rid)
        _check_enum(rule, "determinism", _DETERMINISM, errors, rid)

    return CriteriaLintResult(tuple(errors))


def _check_enum(rule: dict, key: str, allowed: set[str], errors: list[LintError], rid) -> None:
    if key in rule and rule[key] not in allowed:
        errors.append(LintError(
            f"{key} は {sorted(allowed)} のいずれか: {rule[key]!r}", str(rid)))
