**前提条件**: 型が DM（ドメインモデル）のノードが存在する（design ステージ到達済み）
**入力/トリガ**: DM に MOD への依存辺がない（`must_link_to: DM→MOD`）
**期待動作**: RULE-006 ERROR を報告する
**例**: DM-1 が MOD への辺を持たない → `ERROR|...|RULE-006|DM-1|...`
