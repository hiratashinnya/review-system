**前提条件**: 型が NFR のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: NFR が SPEC から被依存辺を受けていない（`must_be_linked_from: NFR←[SPEC]`）
**期待動作**: RULE-006 WARNING を報告する
**例**: NFR-3 を指す SPEC の辺が 1 本も無い → `WARNING|...|RULE-006|NFR-3|...`
