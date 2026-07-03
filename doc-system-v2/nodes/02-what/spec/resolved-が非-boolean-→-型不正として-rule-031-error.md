**前提条件**: 型が FND の構造化ノードが 1 件以上パース済みで、検証ツールが config `fnd_lifecycle.resolved_field`（値 `resolved`）を参照して状態判定を行う段にある。当該ノードの YAML には `resolved` キーが存在する。
**入力/トリガ**: 検証ツールが当該 FND ノードの YAML から `resolved` フィールドを読み、その値が boolean（`true`／`false`）ではない（文字列 `"true"`、数値 `1`、`null` 等）と判明する。
**期待動作**: `resolved` の値が boolean でないとき、型不正として `RULE-031` を ERROR で報告する。非 boolean 値を黙って既定の `false`（unresolved）に解決せず、resolved 判定（SPEC-60-1）も unresolved 判定（SPEC-60-2）も適用しない。
**例**: `id: FND-70, type: FND, resolved: "true"`（boolean ではなく文字列）→ `ERROR|doc-system/04-verification/02-findings.md:120|RULE-031|FND-70|resolved must be boolean, got string "true"` を出力し、当該ノードへ resolved／unresolved 判定を適用しない。
