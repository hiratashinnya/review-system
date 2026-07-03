**前提条件**: 型が PROMPT（プロンプト）のノードが存在する（design ステージ到達済み）
**入力/トリガ**: PROMPT に SPEC への依存辺がない（`must_link_to: PROMPT→SPEC`）
**期待動作**: RULE-006 ERROR を報告する
**例**: PROMPT-1 が SPEC への辺を持たない → `ERROR|...|RULE-006|PROMPT-1|...`
