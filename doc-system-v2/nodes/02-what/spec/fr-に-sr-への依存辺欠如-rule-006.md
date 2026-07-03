**前提条件**: 型が FR のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: FR に SR への依存辺がない（`must_link_to: FR→SR`）
**期待動作**: RULE-006 ERROR を報告する
**例**: FR-3 が SR への辺を持たない → `ERROR|...|RULE-006|FR-3|...`
