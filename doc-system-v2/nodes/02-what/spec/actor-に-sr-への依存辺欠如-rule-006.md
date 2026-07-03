**前提条件**: 型が ACTOR のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: ACTOR に SR への依存辺がない（`must_link_to: ACTOR→SR`）
**期待動作**: RULE-006 ERROR を報告する
**例**: ACTOR-1 が SR への辺を持たない → `ERROR|...|RULE-006|ACTOR-1|...`
