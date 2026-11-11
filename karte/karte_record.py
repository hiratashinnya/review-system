"""カルテの記録と参照。移設した設計理由は .ai/rationale/karte-module-split.md を参照。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .format_error import KarteFormatError
from .int_args import matched_int


@dataclass
class Karte:
    issue: int
    findings: list = field(default_factory=list)
    attempts: list = field(default_factory=list)
    results: list = field(default_factory=list)

    # --- 参照 ---
    def finding(self, finding_id: str):
        return next((item for item in self.findings if item.id == finding_id), None)

    def open_findings(self) -> list:
        return [item for item in self.findings if item.is_open]

    def open_ids(self) -> set:
        return {item.id for item in self.open_findings()}

    def remediation_findings(self) -> list:
        """**この PR で是正が求められている未解消 finding**（Issue #503・単一の集合）。

        verdict の「``clean`` を妨げる未解消」（``status --json`` の ``blocking_findings``）・
        ``check`` の診断網羅要求・無進捗検知は、いずれもこの 1 つの集合を使う。
        除かれるのは **``harm: real`` かつ** ``deferred``/``waived`` のものだけ
        （:data:`CLEARING_HARM`）。``harm: none`` は ``disposition`` を書いても残る。
        """
        return [item for item in self.findings if item.needs_remediation]

    def undecided_findings(self) -> list:
        """``harm: real`` かつ disposition 未決定のまま未解消の finding（Issue #495）。"""
        return [item for item in self.findings if item.needs_disposition]

    def next_seq(self) -> int:
        return max((item.seq for item in self.findings), default=0) + 1

    def next_attempt_number(self) -> int:
        return matched_int(str(max((a.number for a in self.attempts), default=0) + 1), KarteFormatError, "Attempt 番号")

    def attempt(self, number: int):
        for item in self.attempts:
            if item.number == number:
                return item
        return None

    def results_for(self, number: int) -> list:
        return [item for item in self.results if item.attempt == number]

    def touched_of(self, number: int) -> list:
        touched: list = []
        for item in self.results_for(number):
            for entry in item.touched:
                if entry not in touched:
                    touched.append(entry)
        return touched

    def attempts_for_finding(self, finding_id: str) -> list:
        return [item for item in self.attempts if finding_id in item.finding_ids]


def new_karte(issue: int) -> Karte:
    return Karte(issue=int(issue))
