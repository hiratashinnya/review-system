**前提条件**: 型が E（外部エンティティ）のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: E に ACTOR への依存辺がない（`must_link_to: E→ACTOR`）
**期待動作**: RULE-006 ERROR を報告する
**例**: E-1 が ACTOR への辺を持たない → `ERROR|...|RULE-006|E-1|...`
