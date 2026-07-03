**前提条件**: 型が FND の構造化ノードが 1 件以上パース済みで、検証ツールが config `fnd_lifecycle.resolved_field`（値 `resolved`）を参照して状態判定を行う段にある。
**入力/トリガ**: 検証ツールが当該 FND ノードの YAML から `resolved` フィールドを読む。
**期待動作**: `resolved` の値が boolean の `true` のとき、当該 FND を resolved（解消済み）と判定する（この判定結果に対して resolved 系の状態依存ルール〔`fnd_lifecycle.resolved.*`〕が適用される）。
**例**: `id: FND-50, type: FND, resolved: true` → resolved と判定 → SPEC-18-9・SPEC-59 の前提（解消済み FND）が成立する。
