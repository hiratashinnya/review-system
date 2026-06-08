"""P2 基準合成のドメイン型。design/01 §4。

CriteriaPack は PF に渡す公開項（メタ抜き）。MetaIndex は機械が使う id→メタ。
"""
from __future__ import annotations

from dataclasses import dataclass

from .enums import Determinism, Severity, OverrideRule
from .ids import RuleId, Provenance


@dataclass(frozen=True, slots=True)
class RuleMeta:                            # LLM へ渡さない内部メタ
    determinism: Determinism
    severity: Severity
    override: OverrideRule
    enabled: bool


@dataclass(frozen=True, slots=True)
class RuleGuidance:                        # 人 & LLM 共用本文
    summary: str
    checkpoints: tuple[str, ...]
    good_examples: tuple[str, ...]
    bad_examples: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ComposedRule:                        # 毎回合成される導出ルール
    rule_id: RuleId
    title: str
    guidance: RuleGuidance
    meta: RuleMeta
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class PackedRule:                          # PF へ渡す公開項
    rule_id: RuleId
    title: str
    guidance: RuleGuidance


@dataclass(frozen=True, slots=True)
class CriteriaPack:                        # PF へ渡すパック（メタ抜き）
    rules: tuple[PackedRule, ...]

    def contains(self, rule_id: RuleId) -> bool:   # ⑤ rule_id 検証で使う
        return any(r.rule_id == rule_id for r in self.rules)


@dataclass(frozen=True, slots=True)
class MetaIndex:                           # id → メタ（機械が使う）。dict 保持＝キー化しない
    by_rule_id: dict[RuleId, RuleMeta]

    def get(self, rule_id: RuleId) -> RuleMeta | None:
        return self.by_rule_id.get(rule_id)
