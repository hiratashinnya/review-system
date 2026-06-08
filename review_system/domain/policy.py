"""自動化ポリシー（determinism×severity → 適用モード）。schema・design/05・Q24=A。

matrix は det → {severity_token: mode}。severity_token は "*"（全）または error/warning/info。
resolve が None＝該当なし → 仕分けは S2 で HUMAN_ONLY に倒す。
"""
from __future__ import annotations

from dataclasses import dataclass

from .enums import Determinism, Severity, ApplicationMode
from .ids import RuleId


@dataclass(frozen=True, slots=True)
class PolicyMatrix:
    matrix: dict[Determinism, dict[str, ApplicationMode]]   # det → {severity_token: mode}
    overrides: dict[RuleId, ApplicationMode]

    def resolve(
        self, determinism: Determinism, severity: Severity, rule_id: RuleId
    ) -> ApplicationMode | None:
        if rule_id in self.overrides:                      # 個別 override が最優先
            return self.overrides[rule_id]
        row = self.matrix.get(determinism)
        if row is None:
            return None
        return row.get(severity.name.lower()) or row.get("*")
