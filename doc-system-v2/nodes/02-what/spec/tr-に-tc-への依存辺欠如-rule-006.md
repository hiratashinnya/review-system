**前提条件**: 型が TR のノードが存在する（verification ステージが activate 済み）
**入力/トリガ**: TR に TC への依存辺がない（config `must_link_to: TR→TC`・severity error）
**期待動作**: RULE-006 を ERROR で報告する
**例**: `TR-2` が `TC-5` への辺を持たない（どの TC も指していない）→ `ERROR|...|RULE-006|TR-2|...`
