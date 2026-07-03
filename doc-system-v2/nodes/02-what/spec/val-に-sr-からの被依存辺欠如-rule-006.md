**前提条件**: 型が VAL のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: VAL が SR から被依存辺を受けていない（`must_be_linked_from: VAL←[SR]`）
**期待動作**: RULE-006 ERROR を報告する
**例**: VAL-1 を指す SR の辺が 1 本も無い → `ERROR|...|RULE-006|VAL-1|...`
