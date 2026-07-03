**前提条件**: 型が SCM（スキーマ）のノードが存在する（design ステージ到達済み）
**入力/トリガ**: SCM に SPEC への依存辺がない（`must_link_to: SCM→SPEC`）
**期待動作**: RULE-006 ERROR を報告する
**例**: SCM-1 が SPEC への辺を持たない → `ERROR|...|RULE-006|SCM-1|...`
