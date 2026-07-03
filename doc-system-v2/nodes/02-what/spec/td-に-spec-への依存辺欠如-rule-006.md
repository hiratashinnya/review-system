**前提条件**: 型が TD のノードが存在する（verification ステージが activate 済み）
**入力/トリガ**: TD に SPEC への依存辺がない（config `must_link_to: TD→SPEC`・severity error）
**期待動作**: RULE-006 を ERROR で報告する
**例**: `TD-3` が `SPEC-18` への辺を 1 本も持たない → `ERROR|...|RULE-006|TD-3|...`
