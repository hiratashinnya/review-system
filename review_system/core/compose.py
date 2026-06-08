"""P2 基準合成（MVP は org 最小）。design/02・schema。

MVP：org の同 doc_type 兄弟ファイルを union（同 id は先勝ち）し、PF へ渡す CriteriaPack
（メタ抜き）と内部 MetaIndex（id→メタ）に分ける。enabled=False は pack から除外。
方向ゲート・本文矛盾・継承マージ（team/project）は MVP 外（PR8 印・post-MVP）。
"""
from __future__ import annotations

import hashlib

from ..domain.criteria import ComposedRule, CriteriaPack, PackedRule, MetaIndex, RuleMeta
from ..domain.ids import RuleId, ContentHash


def build_pack_and_meta(rules: tuple[ComposedRule, ...]) -> tuple[CriteriaPack, MetaIndex]:
    """合成済みルール列 → (観点パック, メタ表)。同 id は先勝ち union、disabled は pack から除外。"""
    packed: list[PackedRule] = []
    meta: dict[RuleId, RuleMeta] = {}
    seen: set[RuleId] = set()
    for r in rules:
        if r.rule_id in seen:                  # 兄弟 union：同 id は先勝ち（矛盾検出は post-MVP）
            continue
        seen.add(r.rule_id)
        meta[r.rule_id] = r.meta
        if r.meta.enabled:                     # disabled は PF に渡さない
            packed.append(PackedRule(r.rule_id, r.title, r.guidance))
    return CriteriaPack(tuple(packed)), MetaIndex(meta)


def content_hash(rules: tuple[ComposedRule, ...]) -> ContentHash:
    """合成結果の決定的ハッシュ（S6 版スタンプ・再現性）。id＋メタ＋本文要約を採る。"""
    lines = sorted(
        f"{r.rule_id.value}|{r.meta.determinism.value}|{int(r.meta.severity)}|"
        f"{r.meta.override.value}|{r.meta.enabled}|{r.guidance.summary}"
        for r in rules
    )
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return ContentHash(digest)
