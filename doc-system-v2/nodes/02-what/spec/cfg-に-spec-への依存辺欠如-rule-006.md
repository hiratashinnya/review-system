**前提条件**: 型が CFG（設定）のノードが存在する（design ステージ到達済み）
**入力/トリガ**: CFG に SPEC への依存辺がない（`must_link_to: CFG→SPEC`）
**期待動作**: RULE-006 ERROR を報告する
**例**: CFG-1 が SPEC への辺を持たない → `ERROR|...|RULE-006|CFG-1|...`
