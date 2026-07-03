**前提条件**: 型が SR のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: SR が FR・NFR・ACTOR のいずれの source からも被依存辺を受けていない（`must_be_linked_from: SR←[FR,NFR,ACTOR]`＝OR ソースのいずれからも辺が無い）
**期待動作**: RULE-006 WARNING を報告する
**例**: SR-5 を指す FR・NFR・ACTOR の辺が 1 本も無い → `WARNING|...|RULE-006|SR-5|...`
