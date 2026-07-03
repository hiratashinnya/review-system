**前提条件**: 型が VERIFY のノードが存在する（verification ステージ）
**入力/トリガ**: VERIFY に対象要素への依存辺がない（`must_link_to: VERIFY→any`）
**期待動作**: RULE-006 ERROR を報告する（旧 RULE-013）
