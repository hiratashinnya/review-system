"""maintainability_lint が返す不変データ。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    status: str
    detail: str
    baseline_key: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
