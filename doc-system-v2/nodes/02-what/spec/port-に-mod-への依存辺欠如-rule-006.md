**前提条件**: 型が PORT（ポート/インターフェース）のノードが存在する（design ステージ到達済み）
**入力/トリガ**: PORT に MOD への依存辺がない（`must_link_to: PORT→MOD`）
**期待動作**: RULE-006 ERROR を報告する
**例**: PORT-1 が MOD への辺を持たない → `ERROR|...|RULE-006|PORT-1|...`
