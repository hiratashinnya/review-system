**前提条件**: 型が E（外部エンティティ）のノードが存在する（design ステージ到達済み）
**入力/トリガ**: E が ORC から被依存辺を受けていない（`must_be_linked_from: E←[ORC]`）
**期待動作**: RULE-006 WARNING を報告する
**例**: E-1 を指す ORC の辺が 1 本も無い → `WARNING|...|RULE-006|E-1|...`
