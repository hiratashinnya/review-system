**前提条件**: SPEC ノードが存在し、current_stage が verification に達している
**入力/トリガ**: SPEC に TD からの被依存辺がない（`must_be_linked_from: SPEC ← [TD]`）
**期待動作**: RULE-006 WARNING を報告する（旧 RULE-015・config 駆動）

> **被覆（FND-94 G1）**: 本仕様は P-2-2-3（必須辺欠如検出）が `→SPEC-15-1` で詳細化することで被覆される（分析層全面見直しで孤児解消・FND-94 resolved）。
