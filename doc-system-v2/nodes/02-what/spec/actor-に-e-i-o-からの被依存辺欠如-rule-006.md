**前提条件**: 型が ACTOR のノードが存在する（analysis ステージ到達済み）
**入力/トリガ**: ACTOR が E・I・O のいずれの source からも被依存辺を受けていない（`must_be_linked_from: ACTOR←[E,I,O]`＝OR ソースのいずれからも辺が無い）
**期待動作**: RULE-006 WARNING を報告する
**例**: ACTOR-1 を指す E・I・O の辺が 1 本も無い → `WARNING|...|RULE-006|ACTOR-1|...`
