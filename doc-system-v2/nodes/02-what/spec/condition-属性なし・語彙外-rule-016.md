**前提条件**: SPEC または TD ノードが存在する
**入力/トリガ**: SPEC・TD に `condition` 属性がない、または `config.yaml` の `condition_vocab` 外の値が設定されている
**期待動作**: RULE-016 ERROR を報告する（condition が無いのはダメ・未充足の RULE-017 とは別軸）
