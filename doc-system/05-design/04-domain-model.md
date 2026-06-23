# ドメインモデル（DM）

> **型**: DM ／ **必須上流**: TERM（→TERM）・MOD（→MOD）
> spec-inspector のドメイン値オブジェクト型定義（doc-system 設計層・activate_stage: design）。
> `spec_inspector/domain.py`（MOD-1）に実装。FND-96（DM→MOD→D 正規化）で新設。

---

## DM-1: NodeRecord型

<details><summary>⬡ DM-1 · v0.1.0</summary>

```yaml
id: DM-1
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-1
    ref_version: "0.1.0"
  - to: MOD-1
    ref_version: "0.3.0"
```
</details>

**Python クラス**: `NodeRecord`（不変値オブジェクト・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: パース結果の単一ノードを表す不変値オブジェクト。フロントマター YAML の各フィールドと辺情報を保持し、各検査モジュールが消費する。
**フィールド**:
- `id: str` — ノード ID（型 prefix + 連番）
- `type: str` — 型値（MOD / DM / SPEC 等）
- `labels: list[str]` — ラベル群
- `scheduled: str` — スケジュール（空文字＝即時）
- `edges: list[EdgeRecord]` — 依存辺リスト（DM-2）
- `condition: str | None` — condition 属性（SPEC/TD/TC 等のみ）
- `result: str | None` — 実行結果（TR のみ）
- `log_ref: str | None` — ログ参照（TR のみ）
- `suppress: list[str]` — 抑制ルール ID 群
**不変条件**: `id` は非空かつ一意。`edges` の各要素は EdgeRecord。`condition` は config の `condition_vocab` 語彙に属す（保持時は任意・検査は別モジュール）。
**実現する D**: D-4（構造化ノードセット）

---

## DM-2: EdgeRecord型

<details><summary>⬡ DM-2 · v0.1.0</summary>

```yaml
id: DM-2
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-2
    ref_version: "0.1.0"
  - to: MOD-1
    ref_version: "0.3.0"
```
</details>

**Python クラス**: `EdgeRecord`（不変値オブジェクト・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: NodeRecord 内の単一の無名依存辺を表す不変値オブジェクト。参照先 ID と参照時バージョンを保持し、ドリフト検査（MOD-5）が消費する。
**フィールド**:
- `to: str` — 参照先ノード ID（単数）
- `ref_version: str` — 参照時の参照先バッジ x.y
**不変条件**: `to` は非空の単一 ID（配列不可）。`ref_version` は `x.y` 形式の非空文字列。`kind` / `status` フィールドを持たない（無名依存辺）。
**実現する D**: D-4（構造化ノードセット）

---

## DM-3: ViolationRecord型

<details><summary>⬡ DM-3 · v0.3.0</summary>

```yaml
id: DM-3
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-3
    ref_version: "0.1.0"
  - to: MOD-1
    ref_version: "0.3.0"
  - to: FND-100
    ref_version: "0.1.0"
```
</details>

**Python クラス**: `ViolationRecord`（不変値オブジェクト・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: RULE 検査結果の違反 1 件を表す不変値オブジェクト。パース段（MOD-4 parser）と各 checker モジュールが生成し、filter（MOD-6）・reporter（MOD-8）が消費する。
**フィールド**:
- `severity: str` — 深刻度（error / warning）
- `file_ref: str` — 違反検出ファイルパス
- `rule_id: str` — 発火ルール ID（RULE-xxx）
- `node_id: str | None` — 違反ノード ID（ファイル全体違反時は None）
- `message: str` — 違反メッセージ
**不変条件**: `severity` は `error` / `warning` のいずれか。`rule_id` は非空の RULE 識別子。`message` は非空。
**実現する D**: D-5（パース段違反リスト）/ D-6（RULE 違反リスト）/ D-7（カバレッジ計測結果・グラフ網羅性穴リスト部分のみ。FR×condition テーブル部分は DM-5 CoverageReport が担う）

> **改訂理由（MINOR バンプ v0.1→v0.2）**: PR #32 レビュー対応（DM→MOD→D 対称化・FND-100）。D-5（パース段違反リスト・RULE-023〜028）は D-6 と同形の `list[ViolationRecord]` でありながら ViolationRecord 型へ realize されていなかった（DM↔D 被覆の非対称）。型は同一（同じ「もの」＝違反レコード 1 件・発生源差は生成元プロセス P-1/P-2 で既表現）のため新規型を作らず「実現する D」に D-5 を追加。`→MOD-1` ref_version を MOD-1 更新後バッジ "0.3" に追従。`→FND-100` バックリファレンス付与。

> **改訂理由（MINOR バンプ v0.2→v0.3）**: PR #32 再レビュー 🟡 指摘対応。DM-5（CoverageReport）本文が「D-7 の穴リスト部分は DM-3 が担う」と明記しているが、DM-3 の「実現する D」に D-7 が未記載で prose 非対称だった。推奨案 (a) に従い「実現する D」に D-7（穴リスト部分のみ）を追記して対称化。構造変更・edges 変更なし（辺追加不要・D-7 の MOD-1 realize 辺は既存）。

---

## DM-4: ConfigSlice型群

<details><summary>⬡ DM-4 · v0.1.0</summary>

```yaml
id: DM-4
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-4
    ref_version: "0.1.0"
  - to: MOD-1
    ref_version: "0.3.0"
```
</details>

**Python クラス**: `ConfigSlice`（`PhaseStateSlice` / `LinkRuleSlice` / `DecisionSpineSlice` / `AlwaysErrorSlice` / `ConditionSlice` / `RuleActivationSlice` / `ScopeSlice` 等の不変値オブジェクト群を束ねる集約）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: config.yaml の各セクションを型付き値オブジェクトとして表す不変スライス群。config（MOD-2）が組み立て、各検査モジュールが必要なスライスを消費する。
**フィールド**（スライスと対応 D）:
- `PhaseStateSlice` — current_phase / current_stage / phases / stages（D-9 フェーズ・ステージ状態）
- `LinkRuleSlice` — must_link_to / must_be_linked_from（D-10 必須接続規則）
- `DecisionSpineSlice` — decision_spine（D-11 決定スパイン規則）
- `AlwaysErrorSlice` — always_error（D-12 always-error 規則）
- `ConditionSlice` — condition_vocab / coverage_rules（D-13 condition 語彙・網羅規則）
- `RuleActivationSlice` — rule_activation（D-14 ルール発火ステージ表）
- `HubThresholdSlice` — ハブ閾値（D-15 ハブ閾値設定・post-mvp）
- `ScopeSlice` — trace_scope（D-16 走査スコープ設定）
**不変条件**: 各スライスは frozen で生成後に変更不可。参照先 D の必須フィールドを欠かさず保持する。
**実現する D**: D-9（フェーズ・ステージ状態）/ D-10（必須接続規則）/ D-11（決定スパイン規則）/ D-12（always-error 規則）/ D-13（condition 語彙・網羅規則）/ D-14（ルール発火ステージ表）/ D-15（ハブ閾値設定）/ D-16（走査スコープ設定）

---

## DM-5: CoverageReport型

<details><summary>⬡ DM-5 · v0.1.0</summary>

```yaml
id: DM-5
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-5
    ref_version: "0.1.0"
  - to: MOD-1
    ref_version: "0.3.0"
  - to: FND-100
    ref_version: "0.1.0"
```
</details>

**Python クラス**: `CoverageReport`（不変値オブジェクト・`@dataclass(frozen=True)`。FR 行を表す内側 VO `CoverageRow` を保持）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: FR×condition 仕様カバレッジ計測の集計結果を表す不変値オブジェクト。spec_coverage（MOD-17）が生成し、reporter（MOD-8）がカバレッジ点検結果（O-2）として整形・出力する。
**フィールド**:
- `rows: tuple[CoverageRow, ...]` — FR ごとの充足状況行（id 昇順）
- `CoverageRow.fr_id: str` — 対象 FR の ID
- `CoverageRow.required_conditions: tuple[str, ...]` — required な condition 値群
- `CoverageRow.satisfied: tuple[str, ...]` — 実際に SPEC/TD で充足された condition 値群
- `CoverageRow.missing: tuple[str, ...]` — 未充足の required condition 値群
- `CoverageRow.covering_specs: tuple[str, ...]` — 充足元の SPEC/TD ノード ID 群
**不変条件**: `rows` は frozen（生成後変更不可）。各 `CoverageRow.missing` は `required_conditions` の部分集合かつ `satisfied` と素。`fr_id` は非空の FR 識別子。
**実現する D**: D-7（カバレッジ計測結果・FR×condition カバレッジテーブル部分。グラフ網羅性穴リスト部分は DM-3 ViolationRecord が担う）

> **新設理由（FND-100・PR #32 レビュー対応）**: D-7（カバレッジ計測結果）の FR×condition カバレッジテーブル部を表す novel 型。違反でない計測集計値であり ViolationRecord では表せないため別の「もの」として新設（PR1）。MOD-17 が `measure_spec_coverage(...) -> CoverageReport` で型名を既に命名済み。`→FND-100` バックリファレンス付与。

---

## DM-6: InspectionViews型群

<details><summary>⬡ DM-6 · v0.1.0</summary>

```yaml
id: DM-6
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-6
    ref_version: "0.1.0"
  - to: MOD-1
    ref_version: "0.3.0"
  - to: FND-100
    ref_version: "0.1.0"
```
</details>

**Python クラス**: `InspectionViews`（`LinkageView` / `AttributeView` / `DecisionEdgeView` / `AnalysisTopologyView` / `SpecCoverageView` の不変値オブジェクト群を束ねる集約・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: D-4（構造化ノードセット）から射影した各検査ビュースライスを型付き値オブジェクトとして表す不変集約。projector（MOD-13）が `project_views(node_set) -> InspectionViews` で組み立て、各検査モジュールが必要なビューを消費する。DM-4（ConfigSlice 型群）の射影側対応物。
**フィールド**（スライスと対応 D）:
- `LinkageView` — id・type・edges(to)・in_degree・out_degree・全ノード ID 集合・階層 ID パターン（D-17 接続検査ビュー。消費: structure_checker MOD-14）
- `AttributeView` — id・type・condition・result・log_ref・suppress・scheduled・辺メタデータ（D-18 属性検査ビュー。消費: condition_checker MOD-15・verification_checker MOD-16・filter MOD-6）
- `DecisionEdgeView` — 辺の from_id・to・ref_version・参照先バッジ x.y・DD/Q/PEND 義務辺情報（D-19 決定辺ビュー。消費: drift_checker MOD-5）
- `AnalysisTopologyView` — 分析層ノード（type ∈ {I,O,D,P,E}）の id・type・edges(to)（D-20 分析層トポロジビュー。消費: graph_coverage MOD-7）
- `SpecCoverageView` — FR/SPEC/TD の id・condition・edges(to)（D-21 仕様カバレッジビュー。消費: spec_coverage MOD-17）
**不変条件**: 各ビューは frozen で生成後に変更不可。`LinkageView.in_degree` / `out_degree` は非負整数で全ノード ID 集合と整合。各ビューは参照先 D の必須フィールドを欠かさず保持する。D-22（グラフトポロジビュー・post-mvp）は本集約に含めない（labels:[post-mvp]・対象外）。
**実現する D**: D-17（接続検査ビュー）/ D-18（属性検査ビュー）/ D-19（決定辺ビュー）/ D-20（分析層トポロジビュー）/ D-21（仕様カバレッジビュー）

> **新設理由（FND-100・PR #32 レビュー対応）**: D-17〜D-21（各検査ビュー型）を 1 ノードで一括 realize。先例 DM-4（ConfigSlice 型群・D-9〜D-16 を 1 ノード集約）と射影系として構造一致。MOD-13 が `project_views(node_set) -> InspectionViews` で集約戻り値型を既に命名済み。これにより D-17〜D-21 経路の `DM→MOD→D` チェーン欠落を補完。`→FND-100` バックリファレンス付与。
