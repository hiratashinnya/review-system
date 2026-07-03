**前提条件**: ノードの `scheduled` が `config.yaml` の phases に含まれる値
**入力/トリガ**: `index(node.scheduled) > index(current_phase)`
**期待動作**: そのノードに対する全ルールを発火させない（always_error 指定ルール〔RULE-007〕のみ例外）
