**前提条件**: 型が FND の解消済みノード（`resolved: true`）があり、解消時には著者が元の `FND→X`（指摘対象への forward 辺）を削除し `X→FND` の backward 辺に置換する運用である（辺逆転ルール・DD-3。辺の削除・追加は著者の処置であり検証ツールの検証対象ではない）
**入力/トリガ**: 解消済み FND に元の forward 辺（`FND→X`）が残存する（config `fnd_lifecycle.resolved.must_not_link_to`・target: any・severity warning）
**期待動作**: 解消済み FND の forward 辺 `FND→X` が残存するとき、RULE-030 を WARNING で報告する
**例**: `resolved: true` の `FND-50` に `FND-50→SPEC-3` の forward 辺が残っている → `WARNING|...|RULE-030|FND-50|...`
