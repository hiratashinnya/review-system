**前提条件**: 型が SPEC のノードが存在する（requirements ステージ到達済み）
**入力/トリガ**: SPEC が FR・NFR・SPEC のいずれの target へも依存辺を持たない（`must_link_to: SPEC→[FR,NFR,SPEC]`＝OR ターゲットのいずれからも辺が無い）
**期待動作**: RULE-006 ERROR を報告する
**例**: SPEC-40 が FR・NFR・親 SPEC のいずれへも辺を持たない → `ERROR|...|RULE-006|SPEC-40|...`
