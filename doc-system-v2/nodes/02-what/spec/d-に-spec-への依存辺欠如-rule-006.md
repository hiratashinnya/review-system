**前提条件**: 型が D（データストア）のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: D に SPEC への依存辺がない（`must_link_to: D→SPEC`）
**期待動作**: RULE-006 ERROR を報告する
**例**: D-1 が SPEC への辺を持たない → `ERROR|...|RULE-006|D-1|...`
