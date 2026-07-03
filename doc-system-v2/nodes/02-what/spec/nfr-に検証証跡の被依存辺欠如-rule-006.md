**前提条件**: 型が NFR のノードが存在する（verification ステージ）
**入力/トリガ**: NFR が FND/TC/VERIFY のいずれからも被依存辺を受けていない（`must_be_linked_from: NFR ← [FND,TC,VERIFY]`）
**期待動作**: RULE-006 WARNING を報告する（旧 RULE-011）
