**前提条件**: SPEC ノードが存在し、current_stage が verification に達している
**入力/トリガ**: テスタブル（condition 有＝leaf）SPEC に TD からの被依存辺がない（`must_be_linked_from: SPEC ← [TD]`・`applies_when: condition_present`）
**期待動作**: RULE-006 を ERROR で報告する（DD-9 で warning→error 昇格・旧 RULE-015・config 駆動）。対象はテスタブル（condition 有＝leaf）SPEC のみで、傘 SPEC（condition 無）は非テスタブルのため対象外。

> **被覆（FND-94 G1）**: 本仕様は P-2-2-3（必須辺欠如検出）が `→SPEC-15-1` で詳細化することで被覆される（分析層全面見直しで孤児解消・FND-94 resolved）。
