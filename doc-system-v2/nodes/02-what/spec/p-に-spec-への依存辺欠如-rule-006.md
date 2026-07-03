**前提条件**: 型が P（プロセス）のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: P に SPEC への依存辺がない（`must_link_to: P→SPEC`）
**期待動作**: RULE-006 ERROR を報告する
**例**: P-1 が SPEC への辺を持たない → `ERROR|...|RULE-006|P-1|...`
