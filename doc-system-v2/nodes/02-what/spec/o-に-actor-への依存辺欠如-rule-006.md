**前提条件**: 型が O（出力）のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: O に ACTOR への依存辺がない（`must_link_to: O→ACTOR`）
**期待動作**: RULE-006 ERROR を報告する
**例**: O-1 が ACTOR への辺を持たない → `ERROR|...|RULE-006|O-1|...`
