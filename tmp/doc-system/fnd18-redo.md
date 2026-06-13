> 反映先: doc-system/02-what/03-spec.md（v0.3.3 → v0.3.4）

> **著作メモ（reconciliation 向け・版の食い違い）**: 入力ブリーフは SPEC-14 の `ref_version: "0.3"` を指定していたが、実ノードは `⬡ SPEC-14 · v0.2`（既存兄弟 SPEC も FR-1 を `"0.2"` で参照）。RULE-004 は参照先ノードの現在 x.y との一致を要求するため、本著作では実ノード版に合わせ **SPEC-14 への辺は `ref_version: "0.2"`**、**FR-1 への辺は `ref_version: "0.2"`** とした。FND-18 は `v0.1` のため `"0.1"`。FR-1 のノード見出しは `⬡ FR-1 · v0.3` だが、兄弟 SPEC（SPEC-1/2/33/34/35）が一様に `"0.2"` を採用しているためグラフ慣行に合わせた（FR-1 を 0.3 へ昇格した場合は全 SPEC の ref_version を一括更新する別タスクが必要）。

---

## SPEC-52: I-1 完全フィールドスキーマ適合（normal）

<details><summary>⬡ SPEC-52 · v0.1</summary>

```yaml
id: SPEC-52
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-1
    ref_version: "0.2"
  - to: FND-18
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みであり、フィールドスキーマ検証（RULE-025/026/027/028）が当該ノードに対して評価される。
**入力/トリガ**: 検証ツールが、共通必須フィールド（`id` 文字列・非空、`type` 文字列・非空、`labels` リスト・空可、`scheduled` 文字列・空可、`edges` リスト・各エントリに `to` と `ref_version`）を全て備え、かつ型別必須拡張フィールド（SPEC/TD は `condition`、TR は `result` と `log_ref`）も備えたノードを処理する。
**期待動作**: 当該ノードに対して RULE-025・RULE-026・RULE-027・RULE-028 をいずれも発火させず、フィールドスキーマ違反を 0 件として通過する（当該ノード起因のエラー出力なし）。スキーマ違反が他に 0 件ならプロセス終了コードは 0。
**出力フォーマット**: 当該ノード起因の `ERROR|...` 行を一切出力しない（標準出力に当該ノードのスキーマ違反行が現れない）。
**終了コード**: 違反 0 件なら 0。
**例**: ノード `{id: "FR-1", type: "FR", labels: [], scheduled: "", edges: [{to: "SR-2", ref_version: "0.2"}]}` を処理 → `id` 非空文字列・`type` 非空文字列・`labels` 空リスト・`scheduled` 空文字列・`edges` リストで各エントリに `to` と `ref_version` あり（FR は型別拡張フィールドなし）→ RULE-025/026/027/028 いずれも非発火・違反 0 件・終了コード 0。

---

## SPEC-53: 共通必須フィールドの型不正・欠如検出（failure）

<details><summary>⬡ SPEC-53 · v0.1</summary>

```yaml
id: SPEC-53
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みである。`id`・`type` の欠如/空は RULE-025/026 が、edge の `ref_version` 欠如は RULE-027 が担当するため、それらは適合済みとし、本検査は共通必須フィールド `labels`・`scheduled`・`edges` の存在と型のみを評価する。
**入力/トリガ**: 検証ツールが、`labels` が非リスト（例: 文字列）・`scheduled` が非文字列・`edges` が非リスト・またはこれら 3 キーのいずれかが欠如、のいずれか 1 つに該当するノードを処理する。
**期待動作**: 当該違反を RULE-028 ERROR として 1 件出力し、当該ノードに対する後続 RULE 評価を中断する（他ファイル・他ノードの処理は継続）。違反が 1 件以上あればプロセス終了コードは 1。
**出力フォーマット**: `ERROR|{file}:{line}|RULE-028|{id}|{message}`（`|` 区切り 5 フィールド。`{file}` は in-graph 相対パス、`{line}` は当該ノードの `⬡` マーカー行番号、`{message}` は違反フィールド名と期待型を述べる文）。
**終了コード**: 違反ありなら 1。
**例**: ノード `{id: "SPEC-99", type: "SPEC", labels: "foo", scheduled: "", edges: []}`（`labels` が文字列）を `doc-system/02-what/03-spec.md` の当該マーカー行で処理 → `ERROR|doc-system/02-what/03-spec.md:{line}|RULE-028|SPEC-99|field 'labels' must be a list` を 1 件出力し、SPEC-99 の後続 RULE 評価を中断・終了コード 1。

---

## SPEC-14-1: カバレッジテーブルの出力フォーマット（normal）

<details><summary>⬡ SPEC-14-1 · v0.1</summary>

```yaml
id: SPEC-14-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-14
    ref_version: "0.2"
  - to: FND-18
    ref_version: "0.1"
```
</details>

**前提条件**: FR→SPEC→TD のグラフがパース済みで、SPEC-14（カバレッジレポート生成）の `--coverage` 実行によりカバレッジテーブル本体が生成される文脈である。gap（カバレッジ欠如）の別セクション出力は SPEC-14 本体および RULE-017/018 の責務であり、本 SPEC ではテーブル本体のフォーマットのみを規定する。
**入力/トリガ**: 検証ツールを `--coverage` オプションで実行する。
**期待動作**: ヘッダ行 `FR-id | normal | boundary | empty | failure | error` を 1 行出力し、続けて全 FR を FR-id 昇順（接頭辞を除いた数値部の昇順）でソートした各行 `{FR-id} | {✅/⬜} | {✅/⬜} | {✅/⬜} | {✅/⬜} | {✅/⬜}` を出力する。各セルは当該 FR にその condition の SPEC が存在すれば `✅`、不在なら `⬜` とする。
**出力フォーマット**: 1 行目はヘッダ `FR-id | normal | boundary | empty | failure | error`。2 行目以降は FR 1 件につき 1 行で `{FR-id} | {セル} | {セル} | {セル} | {セル} | {セル}`（` | ` 区切り 6 フィールド、列順は normal/boundary/empty/failure/error、セルは `✅` または `⬜`）。行はソートキー FR-id の数値部昇順で並ぶ。
**終了コード**: 0。
**例**: FR-1 に normal/empty/failure/error の SPEC があり boundary がない、FR-2 が次に存在する場合 → 出力は
`FR-id | normal | boundary | empty | failure | error`
`FR-1 | ✅ | ⬜ | ✅ | ✅ | ✅`
`FR-2 | ...`（FR-2 が FR-1 の次の行・id 昇順）→ 終了コード 0。
