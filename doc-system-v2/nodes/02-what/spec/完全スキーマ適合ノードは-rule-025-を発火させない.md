**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みであり、当該ノードは共通必須フィールドと型別必須拡張フィールドを全て備える。
**入力/トリガ**: 検証ツールが、共通必須フィールド（`id`・`type`・`labels`・`scheduled`・`edges`）と型別必須拡張フィールド（SPEC/TD は `condition`、TR は `result` と `log_ref`）を全て備えたノードに RULE-025 を評価する。
**期待動作**: 完全スキーマ適合ノードに対して RULE-025 を発火させない。
**例**: `{id: "FR-1", type: "FR", labels: [], scheduled: "", edges: [{to: "SR-2", ref_version: "0.2"}]}` を処理 → RULE-025 非発火。
