# ドメインモデル（DM）

> **型**: DM ／ **必須上流**: TERM（→TERM）・MOD（→MOD）
> spec-inspector のドメイン値オブジェクト型定義（doc-system 設計層・activate_stage: design）。
> `spec_inspector/domain.py`（MOD-1）に実装。FND-96（DM→MOD→D 正規化）で新設。

---

## DM-1: NodeRecord型

<details><summary>⬡ DM-1 · v0.1</summary>

```yaml
id: DM-1
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-1
    ref_version: "0.1"
  - to: MOD-1
    ref_version: "0.2"
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

<details><summary>⬡ DM-2 · v0.1</summary>

```yaml
id: DM-2
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-2
    ref_version: "0.1"
  - to: MOD-1
    ref_version: "0.2"
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

<details><summary>⬡ DM-3 · v0.1</summary>

```yaml
id: DM-3
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-3
    ref_version: "0.1"
  - to: MOD-1
    ref_version: "0.2"
```
</details>

**Python クラス**: `ViolationRecord`（不変値オブジェクト・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: RULE 検査結果の違反 1 件を表す不変値オブジェクト。各 checker モジュールが生成し、filter（MOD-6）・reporter（MOD-8）が消費する。
**フィールド**:
- `severity: str` — 深刻度（error / warning）
- `file_ref: str` — 違反検出ファイルパス
- `rule_id: str` — 発火ルール ID（RULE-xxx）
- `node_id: str | None` — 違反ノード ID（ファイル全体違反時は None）
- `message: str` — 違反メッセージ
**不変条件**: `severity` は `error` / `warning` のいずれか。`rule_id` は非空の RULE 識別子。`message` は非空。
**実現する D**: D-6（RULE 違反リスト）

---

## DM-4: ConfigSlice型群

<details><summary>⬡ DM-4 · v0.1</summary>

```yaml
id: DM-4
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-4
    ref_version: "0.1"
  - to: MOD-1
    ref_version: "0.2"
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
