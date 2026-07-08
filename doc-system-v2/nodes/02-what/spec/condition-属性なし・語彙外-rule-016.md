**前提条件**: SPEC または TD ノードが存在する
**入力/トリガ**: テスタブルな SPEC・TD に `condition` 属性がない、または `config.yaml` の `condition_vocab` 外の値が設定されている
**期待動作**: RULE-016 ERROR を報告する。ただし、同型 child→parent 辺から傘ロールと機械判定できる非テスタブル SPEC は `condition` 省略を許容し、RULE-016 の対象外とする。未充足の RULE-017 とは別軸である。
