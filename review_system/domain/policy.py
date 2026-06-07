"""自動化ポリシー（determinism×severity → 適用モード）。schema・design/05。

MVP は severity は "*"（一律）。determinism→mode の写像＋ rule 個別 override。
resolve が None を返す＝matrix に無い → 仕分けは S2 で HUMAN_ONLY に倒す。
"""
from __future__ import annotations

from dataclasses import dataclass

from .enums import Determinism, Severity, ApplicationMode
from .ids import RuleId


@dataclass(frozen=True, slots=True)
class PolicyMatrix:
    by_determinism: dict[Determinism, ApplicationMode]   # severity "*"（MVP）
    overrides: dict[RuleId, ApplicationMode]

    def resolve(
        self, determinism: Determinism, severity: Severity, rule_id: RuleId
    ) -> ApplicationMode | None:
        if rule_id in self.overrides:
            return self.overrides[rule_id]
        return self.by_determinism.get(determinism)
