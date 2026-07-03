**前提条件**: 型が FND の構造化ノードが 1 件以上パース済みで、検証ツールが config `fnd_lifecycle.resolved_field`（値 `resolved`）を参照して状態判定を行う段にある。`resolved` キーが存在する場合、その値は boolean である（非 boolean 値の型検証は SPEC-60-3 の責務）。
**入力/トリガ**: 検証ツールが当該 FND ノードの YAML から `resolved` フィールドを読み、その値が boolean の `false` である、または `resolved` キー自体が存在しない。
**期待動作**: `resolved` の値が boolean の `false` であるとき、またはキーが未設定で既定の `false` に解決されるとき、当該 FND を unresolved（未解消）と判定する（config「省略時は false として扱う」の既定適用。この判定結果に対して unresolved 系の状態依存ルール〔`fnd_lifecycle.unresolved.*`〕が適用される）。非 boolean 値はこの既定解決の対象とせず SPEC-60-3（RULE-031 ERROR）で扱う。
**例**: `resolved: false`（boolean）の `FND-60`、および `resolved` キーを持たない `FND-61` → いずれも unresolved と判定 → SPEC-18-1 の前提（未解消 FND）が成立する。一方 `resolved: "false"`（文字列）は本 SPEC の対象外で SPEC-60-3 が型不正を報告する。
