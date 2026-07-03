**前提条件**: 型が SRC のノードが存在する（implementation ステージが activate 済み）
**入力/トリガ**: SRC が DM・PORT・ORC のいずれにも依存辺を張っていない（config `must_link_to: SRC→[DM,PORT,ORC]`〔OR ターゲット〕・severity error）
**期待動作**: RULE-006 を ERROR で報告する。これは `@id` realizes 照合（SPEC-28-1/28-2）による設計漏れ・紐づけ漏れ検出とは別に、config の必須辺 `SRC→[DM,PORT,ORC]` の欠如を構造点検として検出するものである。
**例**: `SRC-4` が DM・PORT・ORC のいずれへも辺を持たない（3 ターゲットすべてに未接続）→ `ERROR|...|RULE-006|SRC-4|...`
