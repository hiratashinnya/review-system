**前提条件**: 型が I（入力）のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: I に SPEC への依存辺がない（`must_link_to: I→SPEC`）
**期待動作**: RULE-006 ERROR を報告する
**例**: I-1 が SPEC への辺を持たない → `ERROR|...|RULE-006|I-1|...`
