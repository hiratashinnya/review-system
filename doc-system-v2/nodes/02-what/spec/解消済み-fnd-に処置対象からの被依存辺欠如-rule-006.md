**前提条件**: 型が FND の解消済みノード（`resolved: true`）が存在する（verification ステージが activate 済み）。解消時には著者が処置対象要素に `X→FND` の backward 辺を付与する運用である（辺逆転ルール・DD-3）
**入力/トリガ**: 解消済み FND がどの処置対象要素からも被依存辺を受けていない（config `fnd_lifecycle.resolved.must_be_linked_from`・source: any・severity error）
**期待動作**: RULE-006 を ERROR で報告する
**例**: `resolved: true` の `FND-50` を指す `X→FND-50` の辺が 1 本も存在しない → `ERROR|...|RULE-006|FND-50|...`
