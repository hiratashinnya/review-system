**前提条件**: 型が NFR のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: NFR が SPEC から被依存辺を受けていない（`must_be_linked_from: NFR←[SPEC]`）
**期待動作**: RULE-006 を ERROR で報告する（DD-9 で warning→error 昇格・NFR は必ず SPEC へ導出される＝設計へ落ちる価値経路の起点）
**例**: NFR-3 を指す SPEC の辺が 1 本も無い → `ERROR|...|RULE-006|NFR-3|...`
