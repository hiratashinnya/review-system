**前提条件**: 型が SR のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: SR に VAL への依存辺がない（`must_link_to: SR→VAL`）
**期待動作**: RULE-006 ERROR を報告する
**例**: SR-1 が VAL への辺を持たない → `ERROR|...|RULE-006|SR-1|...`
