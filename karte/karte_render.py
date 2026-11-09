"""カルテ記録の描画。移設した設計理由は .ai/rationale/karte-module-split.md を参照。"""

from __future__ import annotations

from .attempt_record import Attempt, Result
from .finding_record import Finding
from .karte_record import Karte
from .value_codec import format_value
from .vocabulary import FORMAT_VERSION, SECTION_ATTEMPTS, SECTION_FINDINGS


def _emit(lines: list, key: str, value) -> None:
    lines.append(f"{key}: {format_value(value)}")


def render_finding(finding: Finding) -> str:
    lines = [f"### {finding.id}"]
    _emit(lines, "status", finding.status)
    _emit(lines, "harm", finding.harm)
    _emit(lines, "harm_detail", finding.harm_detail)
    _emit(lines, "severity", finding.severity)
    _emit(lines, "scope", finding.scope)
    _emit(lines, "disposition", finding.disposition)
    _emit(lines, "deferred_to", finding.deferred_to)
    _emit(lines, "waived_by", finding.waived_by)
    _emit(lines, "waived_reason", finding.waived_reason)
    _emit(lines, "locus", finding.locus)
    _emit(lines, "summary", finding.summary)
    _emit(lines, "evidence", finding.evidence)
    _emit(lines, "expected", finding.expected)
    _emit(lines, "recheck", finding.recheck)
    _emit(lines, "rounds", finding.rounds)
    _emit(lines, "resolved_round", "" if finding.resolved_round is None else finding.resolved_round)
    return "\n".join(lines) + "\n"


def render_attempt(attempt: Attempt) -> str:
    lines = [f"### Attempt {attempt.number}"]
    _emit(lines, "round", attempt.round)
    _emit(lines, "finding_ids", attempt.finding_ids)
    _emit(lines, "root_cause", attempt.root_cause)
    _emit(lines, "change_kind", attempt.change_kind)
    _emit(lines, "targets", attempt.targets)
    _emit(lines, "diagnosis", attempt.diagnosis)
    return "\n".join(lines) + "\n"


def render_result(result: Result) -> str:
    lines = [f"### Result {result.attempt}"]
    _emit(lines, "attempt", result.attempt)
    _emit(lines, "finding_ids", result.finding_ids)
    _emit(lines, "touched", result.touched)
    _emit(lines, "outcome", result.outcome)
    _emit(lines, "note", result.note)
    return "\n".join(lines) + "\n"


def dumps(karte: Karte) -> str:
    """カルテ全体を文字列化する（``## Attempts`` を最後に置き、追記が必ずそこに入る）。"""
    parts = [
        f"# Karte: issue-{karte.issue}\n",
        f"<!-- karte-format: {FORMAT_VERSION} -->\n",
        f"\n## {SECTION_FINDINGS}\n",
    ]
    for finding in sorted(karte.findings, key=lambda item: item.seq):
        parts.append("\n" + render_finding(finding))
    parts.append(f"\n## {SECTION_ATTEMPTS}\n")
    blocks = [(item.number, 0, render_attempt(item)) for item in karte.attempts]
    blocks += [(item.attempt, 1, render_result(item)) for item in karte.results]
    for _number, _kind, body in sorted(blocks, key=lambda item: (item[0], item[1])):
        parts.append("\n" + body)
    return "".join(parts)
