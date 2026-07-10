**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みである。`id`・`type` の欠如/空は RULE-025/026 が、edge の `ref_version` 欠如は RULE-027 が担当するため適合済みとし、本検査は共通必須フィールド `labels`・`scheduled`・`edges` の存在と型のみを評価する。
**入力/トリガ**: 検証ツールが、`labels` が非リスト・`scheduled` が非文字列・`edges` が非リスト・またはこれら 3 キーのいずれかが欠如、のいずれか 1 つに該当するノードを処理する。
**期待動作**: 当該違反があるとき、RULE-028 ERROR を 1 件出力する。
**出力フォーマット**: `ERROR|{file}:{line}|RULE-028|{id}|{message}`（`|` 区切り 5 フィールド。`{file}` は in-graph 相対パス、`{line}` は当該ノードの `⬡` マーカー行番号、`{message}` は違反フィールド名と期待型を述べる文）。
**例**: ノード `{id: "SPEC-99", type: "SPEC", labels: "foo", scheduled: "sprint-1", edges: []}`（`labels` が文字列）を `doc-system/02-what/03-spec.md` の当該マーカー行で処理 → `ERROR|doc-system/02-what/03-spec.md:{line}|RULE-028|SPEC-99|field 'labels' must be a list` を 1 件出力。
