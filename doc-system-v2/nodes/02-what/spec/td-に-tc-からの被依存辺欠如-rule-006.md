**前提条件**: 型が TD のノードが存在する（verification ステージが activate 済み）
**入力/トリガ**: TD が TC から被依存辺を受けていない（config `must_be_linked_from: TD ← [TC]`・severity warning）
**期待動作**: RULE-006 を WARNING で報告する
**例**: `TD-3` を指す `TC` ノードが 1 つも存在しない → `WARNING|...|RULE-006|TD-3|...`
