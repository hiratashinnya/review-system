# 用語定義（TERM）

> **型**: TERM ／ **必須上流**: SPEC（依存辺 warning）
> doc-system 設計層の値オブジェクト型に対応する用語定義（activate_stage: analysis）。
> spec-inspector が内部で扱うパース結果・検査結果・設定の各内部表現を語彙として固定する。

---

## TERM-1: NodeRecord

<details><summary>⬡ TERM-1 · v0.1.0</summary>

```yaml
id: TERM-1
type: TERM
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3.0"
```
</details>

**もの**: パース結果として得られる単一ノードの内部表現。1つの `.md` ノードを 1 レコードに射影したもの。
**用途**: パーサ（MOD-4）がフロントマターを解析して生成し、各 checker / coverage / projector が読み取って検査・射影の入力とする。グラフ全体は `list[NodeRecord]` で表す。
**Python 型名**: `NodeRecord`
**保持要素**: `id` / `type` / `labels` / `scheduled` / `edges`（EdgeRecord のリスト）
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）

---

## TERM-2: EdgeRecord

<details><summary>⬡ TERM-2 · v0.1.0</summary>

```yaml
id: TERM-2
type: TERM
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3.0"
```
</details>

**もの**: ノード内に記述された 1 本の無名依存辺の内部表現。`NodeRecord.edges` の各要素。
**用途**: パーサ（MOD-4）がフロントマターの `edges[]` を解析して生成し、drift_checker（参照先版照合）・structure_checker（dangling/必須辺）等が辺の到達先と版を判定するのに用いる。
**Python 型名**: `EdgeRecord`
**保持要素**: `to`（参照先ノード ID・単数）/ `ref_version`（参照先ノードのバッジ x.y）
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）

---

## TERM-3: ViolationRecord

<details><summary>⬡ TERM-3 · v0.1.0</summary>

```yaml
id: TERM-3
type: TERM
labels: []
scheduled: ""
edges:
  - to: SPEC-5
    ref_version: "0.2.0"
```
</details>

**もの**: RULE 検査が検出した違反 1 件の内部表現。検査結果の最小単位。
**用途**: 各 checker（MOD-5/6/14/15/16 等）が違反を検出するたびに 1 レコード生成し、filter（抑制・発火フィルタ）を経て reporter（MOD-8）がレポート・G# 採番・終了コード決定の入力とする。
**Python 型名**: `ViolationRecord`
**保持要素**: `severity` / `file_ref` / `rule_id` / `node_id` / `message`
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）

---

## TERM-4: ConfigSlice

<details><summary>⬡ TERM-4 · v0.1.0</summary>

```yaml
id: TERM-4
type: TERM
labels: []
scheduled: ""
edges:
  - to: SPEC-21
    ref_version: "0.3.0"
```
</details>

**もの**: `config.yaml` の各セクション（フェーズ/ステージ・接続規則・抑制対象外・トレース対象等）を検査ロジックが参照しやすい形に分解した設定値オブジェクト群の総称。
**用途**: config（MOD-2）が `config.yaml` を読込・スキーマ検証して組み立て、各 checker / collector / projector が検査条件（必須辺・activate_stage・severity・always_error・trace_scope 等）を引くために参照する。
**Python 型名**: `ConfigSlice`（D-9〜D-16 各スライスに対応する値オブジェクト群）
**保持要素**: フェーズ/ステージ定義・must_link_to / must_be_linked_from・decision_spine・rule_activation・condition_vocab・coverage_rules・always_error・trace_scope 等のスライス
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）

---

## TERM-5: CoverageReport

<details><summary>⬡ TERM-5 · v0.1.0</summary>

```yaml
id: TERM-5
type: TERM
labels: []
scheduled: ""
edges:
  - to: SPEC-14
    ref_version: "0.2.0"
```
</details>

**もの**: 仕様カバレッジ計測（FR×condition 充足集計）の結果を表す内部表現。各 FR がどの condition で SPEC/TD に充足されているかを集計したテーブル。違反（ViolationRecord）ではなく充足度の計測値である。
**用途**: spec_coverage（MOD-17）が D-21（仕様カバレッジビュー）と D-13（condition 語彙・網羅規則）から FR×condition 充足を集計して生成し、reporter（MOD-8）がカバレッジ点検結果（O-2）の整形に用いる。D-7（カバレッジ計測結果）の後半（FR×condition カバレッジテーブル）の型。前半（グラフ網羅性穴リスト）は ViolationRecord 列（TERM-3）が担う。
**Python 型名**: `CoverageReport`
**保持要素**: FR ごとの行（FR id・required_conditions 充足状況・recommended_conditions 充足状況・充足/未充足の SPEC/TD 参照）と集計サマリ（充足率等）
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）

---

## TERM-6: InspectionViews

<details><summary>⬡ TERM-6 · v0.1.0</summary>

```yaml
id: TERM-6
type: TERM
labels: []
scheduled: ""
edges:
  - to: SPEC-5
    ref_version: "0.2.0"
```
</details>

**もの**: D-4（構造化ノードセット）を検査子向けに射影した検査ビュースライス値オブジェクト群の総称。接続検査・属性検査・決定辺・分析層トポロジ・仕様カバレッジの各ビューを束ねた集約で、各ビューは D-4 の部分射影に固有の計算フィールド（in_degree / out_degree 等）を加えたもの。
**用途**: projector（MOD-13）が D-4 を一括射影して組み立て、各 checker / coverage / projector 消費側（structure_checker・condition_checker・verification_checker・drift_checker・graph_coverage・spec_coverage）が必要なビューだけを受け取って検査入力とする。DM-4（ConfigSlice 型群）が config を分解した集約であるのに対し、InspectionViews は D-4 を分解した射影側の集約。
**Python 型名**: `InspectionViews`（D-17〜D-21 各ビューに対応する値オブジェクト群を束ねる集約）
**保持要素**: `LinkageView`（D-17 接続検査）・`AttributeView`（D-18 属性検査）・`DecisionEdgeView`（D-19 決定辺）・`AnalysisTopologyView`（D-20 分析層トポロジ）・`SpecCoverageView`（D-21 仕様カバレッジ）の各スライス
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）

> **TERM→SPEC 上流の根拠**: D-17（接続検査ビュー）の上流 SPEC-5 を集約代表として張る（DM-4↔TERM-4 が代表 SPEC を 1 本張る先例に倣う）。D-18〜D-21 の各上流（SPEC-15/9/29/14）はビュー単位 D ノード側で既に表現済み。
