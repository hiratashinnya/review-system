> SPEC 著作出力（spec-author）。reconciliation が `doc-system/02-what/03-spec.md` 等へ転記する。
> ref_version 規約：FR への辺 = `"0.2"`（FR ファイル 0.2.x）／親 SPEC への辺 = `"0.3"`（SPEC ファイル 0.3.x）。
> 全 SPEC は無名依存辺・condition 属性必須・1アサーション1ノード。

---

## SPEC-1 書き直し（v0.2 → v0.3）

<details><summary>⬡ SPEC-1 · v0.3</summary>

```yaml
id: SPEC-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルが1件以上存在し、当該ファイルに `<details><summary>⬡ PREFIX-N` 形式の行が存在し、その直後に ```` ```yaml ```` ブロックがあり PyYAML safe_load でパース可能である。
**入力/トリガ**: 検証ツールが当該 in-graph ファイルを処理する。
**期待動作**: `⬡` マーカー直後の YAML ブロックから `id`・`type`・`labels`・`scheduled`・`edges` を持つ構造化ノードを1件生成する。マーカー行の `PREFIX-N` と YAML の `id` 値が一致する。RULE-023〜027 の違反がなければエラー出力なし。
**例**: `doc-system/02-what/03-spec.md` 行15に `⬡ SPEC-1 · v0.3`、直後 YAML に `id: SPEC-1, type: SPEC` → ノード `{id:"SPEC-1", type:"SPEC", labels:[], scheduled:"", edges:[{to:"FR-1", ref_version:"0.2"}]}` を生成し、エラー出力なし。

---

## SPEC-2 書き直し（v0.2 → v0.3・RULE-023 限定）

<details><summary>⬡ SPEC-2 · v0.3</summary>

```yaml
id: SPEC-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカー行が存在し、その直後の YAML ブロック自体は存在する（マーカー欠落ではなく中身の構文不正のケース）。
**入力/トリガ**: その YAML ブロックが PyYAML safe_load で ScannerError または ParserError を発生させる（インデント不正・コロン欠如等）。
**期待動作**: `ERROR|{file}:{line}|RULE-023|(none)|YAML parse error: {例外メッセージ}` を1件出力し、当該ファイルのパースを中断する（fail-close）。後続 RULE-024〜027 を当該ファイルに発火させない。他 in-graph ファイルの処理は継続する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に不正インデント → `ERROR|doc-system/02-what/01-fr.md:17|RULE-023|(none)|YAML parse error: mapping values are not allowed here` を出力し、当該ファイルの後続ノードを生成しない。

---

## SPEC-26 書き直し（v0.2 → v0.3）

<details><summary>⬡ SPEC-26 · v0.3</summary>

```yaml
id: SPEC-26
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-11
    ref_version: "0.2"
```
</details>

**前提条件**: `templates/<layer>/<type>.md` が存在する（layer ∈ {requirements, analysis, design, verification}、type はその層の型名。例 `templates/requirements/SPEC.md`）。
**入力/トリガ**: 著者がテンプレートを複製してノード著作を開始する。
**期待動作**: テンプレートが以下を全て含む — `id:`（プレースホルダ）、`type:`（型名）、`labels: []`、`scheduled: ""`、`edges:`（≥1エントリ・各エントリに `to:` と `ref_version:`）、本文4項目（`**前提条件**:`／`**入力/トリガ**:`／`**期待動作**:`／`**例**:`）。複製した初期状態で RULE-025／026／027 が発火しない。
**例**: `templates/requirements/SPEC.md` を複製すると `id: SPEC-XXX`（プレースホルダ）・`type: SPEC`・`edges: [{to: FR-XX, ref_version: "0.0"}]` が存在し、複製直後のノードに対し RULE-025／026／027 がいずれも発火しない。

---

## SPEC-27 書き直し（v0.2 → v0.3・辺を FR-11 → FR-13 に変更）

<details><summary>⬡ SPEC-27 · v0.3</summary>

```yaml
id: SPEC-27
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-13
    ref_version: "0.2"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義（例 `requirements-author.md`）が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: エージェントが外部ファイル参照なしに以下を全て提供する — 対象型の `type` 値・`id` PREFIX パターン・必須辺方向（`to` 先の型と方向）・本文4項目フォーマット・RULE チェックリスト。出力は `tmp/<sprint>/<parent-id>.md` に書かれ、reconciliation が本ファイルへ転記する。
**例**: `requirements-author` に FR 著作を依頼 → `type: FR`・`edges[].to: SR-*`（SR 辺必須）・4項目本文の指示がエージェント定義に内包され、`config.yaml` や `authoring-guide.md` を読まずに著作できる。

---

## SPEC-31 新規（→FR-1, empty）

<details><summary>⬡ SPEC-31 · v0.1</summary>

```yaml
id: SPEC-31
type: SPEC
labels: []
scheduled: ""
condition: empty
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: `config.yaml` の `trace_scope` 設定の結果、in-graph ファイルが0件になる。
**入力/トリガ**: 検証ツールを実行する。
**期待動作**: 違反0件・ノード0件を報告し、終了コード 0 で終了する。RULE-005〜027 の評価を全てスキップする。
**例**: `trace_scope.include: ["doc-system/**/*.md"]` かつ `exclude: ["doc-system/**/*.md"]` → in-graph ファイル0件・ノード0件・違反0件・終了コード 0。

---

## SPEC-32 新規（→FR-1, error・RULE-024）

<details><summary>⬡ SPEC-32 · v0.1</summary>

```yaml
id: SPEC-32
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカー行が1件以上存在する。
**入力/トリガ**: `⬡` マーカー行の直後行が ```` ```yaml ```` ブロック開始行でない（heading／空行＋heading／別の `⬡` マーカーが直後に来る）。
**期待動作**: `ERROR|{file}:{line}|RULE-024|(none)|⬡ marker at line N has no YAML block following` を出力し、当該ファイルのパースを中断する（fail-close）。
**例**: `doc-system/03-analysis/02-io.md` 行20に `⬡ I-1 · v0.3`、行21が `## I-2:` → `ERROR|doc-system/03-analysis/02-io.md:20|RULE-024|(none)|⬡ marker at line 20 has no YAML block following`。

---

## SPEC-33 新規（→FR-1, error・RULE-025）

<details><summary>⬡ SPEC-33 · v0.1</summary>

```yaml
id: SPEC-33
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと直後の YAML ブロックが存在し、YAML は PyYAML safe_load でパース可能である。
**入力/トリガ**: YAML ブロックに `id` キーが存在しない、または値が空文字列（`id: ""`）である。
**期待動作**: `ERROR|{file}:{line}|RULE-025|(none)|id field missing or empty` を出力し、当該ノードの後続 RULE 評価を中断する（他ファイル・他ノードは継続）。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に id キーなし → `ERROR|doc-system/02-what/01-fr.md:17|RULE-025|(none)|id field missing or empty`。

---

## SPEC-34 新規（→FR-1, error・RULE-026）

<details><summary>⬡ SPEC-34 · v0.1</summary>

```yaml
id: SPEC-34
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと YAML ブロックが存在し、YAML パース可能で `id` キーは存在する。
**入力/トリガ**: YAML ブロックに `type` キーが存在しない、または値が空文字列である。
**期待動作**: `ERROR|{file}:{line}|RULE-026|{id}|type field missing or empty` を出力し、当該ノードの後続 RULE 評価を中断する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に type なし・id は `FR-1` → `ERROR|doc-system/02-what/01-fr.md:17|RULE-026|FR-1|type field missing or empty`。

---

## SPEC-35 新規（→FR-1, failure・RULE-027）

<details><summary>⬡ SPEC-35 · v0.1</summary>

```yaml
id: SPEC-35
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに YAML ブロックが存在し、`id`・`type` は存在する。`edges` リストに1件以上のエントリがある。
**入力/トリガ**: `edges` の任意のエントリに `ref_version` キーが存在しない。
**期待動作**: `ERROR|{file}:{line}|RULE-027|{id}|edge to {target_id}: ref_version missing` を出力し、当該ノードの後続 RULE 評価を中断する。
**例**: `doc-system/02-what/03-spec.md` の SPEC-1 ノードの edges に `{to: FR-1}`（ref_version なし）→ `ERROR|doc-system/02-what/03-spec.md:22|RULE-027|SPEC-1|edge to FR-1: ref_version missing`。

---

## SPEC-36 新規（→FR-11, failure）

<details><summary>⬡ SPEC-36 · v0.1</summary>

```yaml
id: SPEC-36
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-11
    ref_version: "0.2"
```
</details>

**前提条件**: テンプレート `templates/<layer>/<type>.md` の `id:` または `type:` フィールドが削除されている、または空になっている。
**入力/トリガ**: 著者がそのテンプレートを複製してノードを著作し、検証ツールが当該ノードを処理する。
**期待動作**: テンプレート由来で必須フィールドを欠くため、RULE-025（id 欠如）または RULE-026（type 欠如）の ERROR が報告される。
**例**: `templates/requirements/FR.md` の `id:` 行が削除 → 著者が複製して `doc-system/02-what/01-fr.md` 行14に著作 → `ERROR|doc-system/02-what/01-fr.md:14|RULE-025|(none)|id field missing or empty`。

---

## SPEC-38 新規（→FR-13, normal）

<details><summary>⬡ SPEC-38 · v0.1</summary>

```yaml
id: SPEC-38
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-13
    ref_version: "0.2"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義（例 `requirements-author.md`）が存在し、著者が FR 著作を依頼する。
**入力/トリガ**: 著者が `requirements-author` エージェントに FR ノード1件の著作を依頼する。
**期待動作**: エージェントは `type: FR`・`id: FR-N`（連番）・`edges: [{to: SR-*, ref_version: "..."}]`・本文4項目を含むノードを `tmp/sprint-1/<parent-id>.md` に出力する。出力後、reconciliation が本ファイルに転記する。
**例**: `requirements-author` に「FR-13 著作」を依頼 → `tmp/sprint-1/fr-11-13-14.md` に `id: FR-13, type: FR, edges: [{to: SR-1, ref_version: "0.2"}]` ＋4項目本文が出力される。

---

## SPEC-39 新規（→FR-13, failure）

<details><summary>⬡ SPEC-39 · v0.1</summary>

```yaml
id: SPEC-39
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-13
    ref_version: "0.2"
```
</details>

**前提条件**: 著者がエージェントに著作を依頼し、エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力する。
**入力/トリガ**: reconciliation エージェントが tmp ファイルを検証する際に、id フィールドの欠如を検出する。
**期待動作**: reconciliation は検証エラーを報告し、本ファイルへの転記を中断する。`id field missing or empty` を出力する（RULE-025 相当のチェックを reconciliation 検証フェーズで実施）。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → `ERROR|tmp/sprint-1/fr-11-13-14.md:5|RULE-025|(none)|id field missing or empty` を報告し、本ファイルへの転記を中断する。

---

## SPEC-40 新規（→FR-14, normal・post-mvp）

<details><summary>⬡ SPEC-40 · v0.1</summary>

```yaml
id: SPEC-40
type: SPEC
labels: [post-mvp]
scheduled: "post-mvp"
condition: normal
edges:
  - to: FR-14
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイル A の version x.y が上昇し、ノード B が `to: A, ref_version: "旧 x.y"` の辺を持つ（RULE-004 ドリフト状態）。
**入力/トリガ**: 著者が `--propagate A` オプションで検証ツールを実行する（post-MVP 機能）。
**期待動作**: RULE-004 ドリフトが検出されたノード B の一覧と、各ノードで更新が必要な `ref_version` の現在値・更新先値を表形式で出力する。`{node-id} | {file}:{line} | ref_version: "{old}" → "{new}"` 形式で表示する。
**例**: `doc-system/03-analysis/02-io.md` の version が `0.5`→`0.6` に上昇したとき `P-1 | doc-system/03-analysis/03-processes.md:26 | ref_version: "0.5" → "0.6"` の一覧を出力する。

---

## 親ノード更新メモ（reconciliation 向け）

親 FR-1／FR-11／FR-13／FR-14 は子 SPEC への辺を持たない（階層は ID パターンで表現・DD-014）。
SPEC-27 の辺は FR-11 → FR-13 へ付け替え済み（本ファイル該当節）。
