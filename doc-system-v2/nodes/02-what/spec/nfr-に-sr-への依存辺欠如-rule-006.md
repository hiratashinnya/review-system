**前提条件**: 型が NFR のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: NFR に SR への依存辺がない（`must_link_to: NFR→SR`）
**期待動作**: RULE-006 ERROR を報告する
**例**: NFR-3 が SR への辺を持たない → `ERROR|...|RULE-006|NFR-3|...`
