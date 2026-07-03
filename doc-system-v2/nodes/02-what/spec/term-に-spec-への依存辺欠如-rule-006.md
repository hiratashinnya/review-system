**前提条件**: 型が TERM のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: TERM に SPEC への依存辺がない（`must_link_to: TERM→SPEC`）
**期待動作**: RULE-006 WARNING を報告する
**例**: TERM-1 が SPEC への辺を持たない → `WARNING|...|RULE-006|TERM-1|...`
