# 05-static: スキーマ・設定・プロンプトノード

設計層の静的構造ノード（SCM／CFG／PROMPT）を集約するファイル。SCM はノードフォーマット・config.yaml・出力形式のスキーマを定義し、CFG は config.yaml 設定の実インスタンスを要素単位でノード化し、PROMPT は各著作エージェントへの著作支援プロンプト仕様を記録する。

---

## SCM（スキーマ）

## SCM-1: ノードフォーマットスキーマ（傘）

<details><summary>⬡ SCM-1 · v0.1.0</summary>

```yaml
id: SCM-1
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-1
    ref_version: "0.3"
```
</details>

in-graph ノード（I-1 ノードファイル群）が満たすべきフォーマット規約の傘スキーマ。検証ツールが 1 件のノードを正しくパース・構造化できる前提（記法・YAML 構造）を定義する。具体スキーマは配下の子に分割する：SCM-1-1（ノード YAML ブロックの必須フィールド・型）／SCM-1-2（ノードファイルの Markdown 記法＝`<details><summary>⬡ PREFIX-N · vX.Y.Z</summary>` マーカーと YAML 位置・本文配置）。階層は -N 採番で表現し親→子辺は持たない。

**フォーマット**: Markdown（`<details>` ブロック）＋埋め込み YAML
**必須フィールド**: 傘ノードのため固有フィールドは持たない（具体は SCM-1-1・SCM-1-2 が規定）

---

## SCM-1-1: ノード YAML ブロックスキーマ

<details><summary>⬡ SCM-1-1 · v0.1.0</summary>

```yaml
id: SCM-1-1
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-33
    ref_version: "0.1"
  - to: SPEC-34
    ref_version: "0.1"
  - to: SPEC-35
    ref_version: "0.1"
  - to: SPEC-36
    ref_version: "0.1"
  - to: SPEC-52
    ref_version: "0.1"
  - to: SPEC-53
    ref_version: "0.1"
```
</details>

`⬡ PREFIX-N` マーカー直後の YAML ブロックが満たすべきフィールドスキーマ。検証ツールのスキーマ検証（P-1-4・RULE-025/026/027/028）が判定する共通必須フィールドの集合・型・各辺の形式を定義する。これにより型不正・必須欠如のノードが後段検査へ持ち込まれない。

**フォーマット**: PyYAML safe_load でパース可能な YAML マップ
**必須フィールド**:
- `id`（文字列・非空。`PREFIX-N[-N...]` 形式・RULE-025）
- `type`（文字列・非空。型ドメイン値＝SCM/CFG/PROMPT 等の prefix に対応・RULE-026）
- `labels`（リスト。空可 `[]`）
- `scheduled`（文字列。空可 `""`・値は config の phases ドメインに属すこと）
- `edges`（リスト。各エントリは `to`（参照先 ID・単数）と `ref_version`（参照先バッジの x.y・RULE-027）を必須とする。`kind`/`status` は持たない＝無名依存辺）
- 型別拡張：SPEC/TD は `condition`、TR は `result`・`log_ref`（RULE-028 で型・欠如を検証）

---

## SCM-1-2: ノードファイル記法スキーマ

<details><summary>⬡ SCM-1-2 · v0.1.0</summary>

```yaml
id: SCM-1-2
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: SPEC-32
    ref_version: "0.1"
```
</details>

in-graph ノードファイル（.md）の Markdown 記法スキーマ。1 ノードを区切るマーカー行・YAML ブロックの配置・本文の位置を定義し、検証ツールのマーカー走査（P-1-2）と YAML パース（P-1-3）が境界を確定できるようにする。マーカー直後に YAML ブロックがない場合は RULE-024（SPEC-32）で fail-close する。

**フォーマット**: Markdown（`<details>`/`<summary>` 要素＋fenced code block）
**必須フィールド（記法要素）**:
- マーカー行：`<details><summary>⬡ PREFIX-N · vX.Y.Z</summary>`（`⬡` 記号＋ノード ID＋可視バッジ `vMAJOR.MINOR.PATCH`）
- YAML ブロック：マーカー行の直後に ```` ```yaml ```` フェンスで開始し、ノードの構造化フィールド（SCM-1-1）を内包する（マーカー直後に YAML 欠如のとき RULE-024 ERROR）
- 終了：`</details>` でブロックを閉じる
- 本文：`</details>` 以降に Markdown 散文で目的・属性を記述する（任意・人間可読用で構造化対象外）
- 見出し：当該ノードのセクション見出し `## PREFIX-N: タイトル` を YAML の `id` と一致させる

---

## SCM-2: config.yaml スキーマ（傘）

<details><summary>⬡ SCM-2 · v0.1.0</summary>

```yaml
id: SCM-2
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

ドキュメントシステムのグローバル設定ファイル `config.yaml`（I-5）が満たすべきトップレベル構造の傘スキーマ。検証ツール（P-5 設定読込・検証）がルール発火・抑制・必須接続を判定するために読む全セクションの構造を定義する。具体スキーマは配下の子に分割する：SCM-2-1（接続ルール＝must_link_to／must_be_linked_from）／SCM-2-2（ライフサイクル・決定スパイン＝fnd_lifecycle／decision_spine）／SCM-2-3（ステージ・語彙・カバレッジ・スコープ＝current_phase/current_stage/phases/stages/rule_activation/condition_vocab/coverage_rules/always_error/trace_scope）。階層は -N 採番で表現し親→子辺は持たない。

**フォーマット**: YAML（単一ファイル `docs/doc-system/config.yaml`）
**必須フィールド（トップレベルセクション）**: current_phase・current_stage・phases・stages・must_link_to・must_be_linked_from・fnd_lifecycle・decision_spine・rule_activation・condition_vocab・coverage_rules・always_error・trace_scope（詳細は SCM-2-1〜2-3 が規定）

---

## SCM-2-1: 接続ルールスキーマ

<details><summary>⬡ SCM-2-1 · v0.1.0</summary>

```yaml
id: SCM-2-1
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

config.yaml の必須接続セクション（`must_link_to`＝依存辺／`must_be_linked_from`＝被依存辺）の構造スキーマ。RULE-006（必須辺欠如）が config 駆動で判定する各規則行の形を定義する。同一 node の複数行は AND、target/source の配列は OR を意味する。

**フォーマット**: YAML（マップのリスト×2 セクション）
**必須フィールド**:
- `must_link_to`：規則行リスト。各行 `{ node, target, activate_stage, severity, reason }`
  - `node`（型名・規則の主体）・`target`（依存先の型名。配列なら OR）・`activate_stage`（発火開始ステージ・stages のいずれか）・`severity`（`error` | `warning`）・`reason`（説明文字列）
- `must_be_linked_from`：規則行リスト。各行 `{ node, source, activate_stage, severity, reason }`
  - `node`（型名）・`source`（被依存元の型名群。配列＝OR）・`activate_stage`・`severity`・`reason`

---

## SCM-2-2: ライフサイクル／決定スパインスキーマ

<details><summary>⬡ SCM-2-2 · v0.1.0</summary>

```yaml
id: SCM-2-2
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

config.yaml の状態依存ルールセクション（`fnd_lifecycle`＝FND の解消状態に応じた辺向き逆転ルール／`decision_spine`＝DD/Q/PEND の義務辺ルール）の構造スキーマ。FND の resolved 状態で必須辺の向きが逆転すること、および意思決定ノードの反映漏れ（RULE-001/002/022）を判定する規則の形を定義する。

**フォーマット**: YAML（`fnd_lifecycle`＝ネストしたマップ／`decision_spine`＝マップのリスト）
**必須フィールド**:
- `fnd_lifecycle`：
  - `resolved_field`（FND の機械判定フィールド名・既定 `resolved`）
  - `unresolved.must_link_to`（`{ target, activate_stage, severity, reason }`・未解消 FND の forward 辺必須）
  - `resolved.must_be_linked_from`（`{ source, activate_stage, severity, reason }`・処置対象からの backward 辺必須）
  - `resolved.must_not_link_to`（`{ target, activate_stage, severity, reason }`・元 forward 辺の不在期待）
- `decision_spine`：規則行リスト。各行 `{ node, rule, severity }`（`node`＝DD|Q|PEND・`rule`＝RULE 番号・`severity`）

---

## SCM-2-3: ステージ／語彙／カバレッジ／スコープスキーマ

<details><summary>⬡ SCM-2-3 · v0.1.0</summary>

```yaml
id: SCM-2-3
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

config.yaml のステージ制御・属性語彙・カバレッジ・抑制・走査スコープ系セクションの構造スキーマ。現在地（current_phase/current_stage）、有効値ドメイン（phases/stages）、属性ルールの発火制御（rule_activation）、condition 語彙とカバレッジ要件（condition_vocab/coverage_rules）、抑制不可ルール（always_error）、トレース対象集合（trace_scope）の形を定義する。

**フォーマット**: YAML（スカラ・リスト・マップの混在）
**必須フィールド**:
- `current_phase`（文字列・phases のいずれか）・`current_stage`（文字列・stages のいずれか）
- `phases`（有効スプリント名の文字列リスト）・`stages`（有効ステージ名の文字列リスト・順序が発火判定の序列）
- `rule_activation`（マップ。`RULE-XXX: ステージ名`＝属性ルールの発火開始ステージ）
- `condition_vocab`（文字列リスト。例 `[normal, boundary, empty, failure, error]`）
- `coverage_rules`（マップ。型ごとの `required_conditions`／`recommended_conditions` リスト）
- `always_error`（抑制不可 RULE 番号のリスト。例 `[RULE-005, RULE-007]`）
- `trace_scope`（マップ。`include`／`exclude` の glob パターン文字列リスト）

---

## SCM-3: 出力フォーマットスキーマ（傘）

<details><summary>⬡ SCM-3 · v0.1.0</summary>

```yaml
id: SCM-3
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-25
    ref_version: "0.2"
```
</details>

検証ツールが系外アクタ（レビュアー ACTOR-2）へ返す出力（O-1 RULE 違反レポート・O-2 カバレッジ点検結果）の整形フォーマットを定義する傘スキーマ。具体スキーマは配下の子に分割する：SCM-3-1（RULE 違反レポートの 1 行形式・G# 採番・深刻度順整列）／SCM-3-2（カバレッジ結果のテーブル形式・FR×condition 充足）。階層は -N 採番で表現し親→子辺は持たない。

**フォーマット**: プレーンテキスト（stdout・行指向）
**必須フィールド**: 傘ノードのため固有フィールドは持たない（具体は SCM-3-1・SCM-3-2 が規定）

---

## SCM-3-1: RULE 違反レポート行形式

<details><summary>⬡ SCM-3-1 · v0.1.0</summary>

```yaml
id: SCM-3-1
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-25
    ref_version: "0.2"
```
</details>

RULE 違反レポート（O-1）の 1 違反あたりの出力行形式スキーマ。P-4-3（G 番号付与・整形）が生成する各行のフィールド構成と整列規則を定義する。違反一覧は深刻度順（ERROR→WARNING→INFO）に整列して出力する。

**フォーマット**: テキスト 1 違反 = 1 行（` ` 区切りのフィールド列）
**必須フィールド（行構成）**:
- `G{N}`：違反の通し番号（G 番号・出力順に採番）
- `[{severity}]`：深刻度（`ERROR` | `WARNING` | `INFO`。深刻度順に整列）
- `{file}:{line}`：違反箇所のファイルパスと行番号（ノード起因でなければ `(none)` 等）
- `RULE-{N}`：違反した RULE 番号
- `node={id}`：対象ノード ID（不明時は `(none)`）
- `{msg}`：違反内容の説明メッセージ
- 行テンプレート：`G{N} [{severity}] {file}:{line} RULE-{N} node={id}: {msg}`

---

## SCM-3-2: カバレッジ結果形式

<details><summary>⬡ SCM-3-2 · v0.1.0</summary>

```yaml
id: SCM-3-2
type: SCM
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-14
    ref_version: "0.2"
```
</details>

カバレッジ点検結果（O-2・`--coverage` 出力）のテーブル形式スキーマ。FR ごとに condition 軸で SPEC の充足状況を表にした出力の構造を定義する。明細行は FR-id の数値部昇順でソートして出力する。

**フォーマット**: テキストテーブル（` | ` 区切り・1 FR = 1 行）
**必須フィールド（テーブル構成）**:
- ヘッダ行：`FR-id | normal | boundary | empty | failure | error`（6 フィールド・列順は condition_vocab に従う）
- 明細行：`{FR-id} | {セル} | {セル} | {セル} | {セル} | {セル}`（列順 normal/boundary/empty/failure/error）
- セル値：当該 FR にその condition の SPEC が存在すれば `✅`、不在なら `⬜`
- 行順序：FR-id の数値部昇順

---

## CFG（設定）

## CFG-1: config.yaml 設定インスタンス（傘）

<details><summary>⬡ CFG-1 · v0.1.0</summary>

```yaml
id: CFG-1
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
ドキュメントシステム検証ツールが読み込むグローバル設定の単一インスタンス。SCM-2 スキーマに準拠し、ルール発火・抑制・ステージ判定・接続検査・ライフサイクルの全パラメータをここに集約する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: トップレベル13要素を配下の子 CFG に分解。`current_phase`（CFG-1-1）・`current_stage`（CFG-1-2）・`phases`（CFG-1-3）・`stages`（CFG-1-4）・`must_link_to`（CFG-1-5）・`must_be_linked_from`（CFG-1-6）・`fnd_lifecycle`（CFG-1-7）・`decision_spine`（CFG-1-8）・`rule_activation`（CFG-1-9）・`condition_vocab`（CFG-1-10）・`coverage_rules`（CFG-1-11）・`always_error`（CFG-1-12）・`trace_scope`（CFG-1-13）。

---

## CFG-1-1: current_phase

<details><summary>⬡ CFG-1-1 · v0.1.0</summary>

```yaml
id: CFG-1-1
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
現在進行中のスプリント（フェーズ）を示す単一の文字列値。検証ツールがノードの `scheduled` 値と突き合わせ、当該フェーズで有効・繰り越しのいずれかを判定する基準となる。値は `phases`（CFG-1-3）の要素のいずれかでなければならない。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `current_phase: "sprint-1"`（現在値）。スプリント進行に応じてオーナー判断で更新する。

---

## CFG-1-2: current_stage

<details><summary>⬡ CFG-1-2 · v0.1.0</summary>

```yaml
id: CFG-1-2
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
現在のステージ（requirements / analysis / design / implementation / verification のいずれか）を示す単一の文字列値。各接続ルール・属性検査ルールの `activate_stage` と比較され、current_stage がその段階以上に達して初めて当該ルールが発火する（段階ゲートの基準点）。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `current_stage: "design"`（現在値）。`stages`（CFG-1-4）の要素のいずれか。

---

## CFG-1-3: phases

<details><summary>⬡ CFG-1-3 · v0.1.0</summary>

```yaml
id: CFG-1-3
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
プロジェクトで定義されるスプリント（フェーズ）の一覧。`current_phase`（CFG-1-1）およびノードの `scheduled` 値が取りうる有効な語彙を画定する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `phases: [sprint-1, sprint-2, sprint-3]`。

---

## CFG-1-4: stages

<details><summary>⬡ CFG-1-4 · v0.1.0</summary>

```yaml
id: CFG-1-4
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
開発ライフサイクルのステージを定義順に並べた一覧。`current_stage`（CFG-1-2）と各ルールの `activate_stage` が取りうる語彙、およびその順序（段階ゲートの大小比較の基準）を画定する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `stages: [requirements, analysis, design, implementation, verification]`（記載順がそのまま段階順序）。

---

## CFG-1-5: must_link_to

<details><summary>⬡ CFG-1-5 · v0.1.0</summary>

```yaml
id: CFG-1-5
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-1
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
各ノード型に課す必須の依存辺（node → target）ルール群の実インスタンス。requirements 骨格から verification までの全段階を、`node`・`target`・`activate_stage`・`severity`・`reason` の5項目で列挙する。同一 node の複数行は AND（各行が独立検査）、target が配列なら OR（いずれか1本以上）として評価される。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `must_link_to:` 配下のルール行群。例＝`{ node: CFG, target: SCM, activate_stage: design, severity: error }`・`{ node: SPEC, target: [FR, NFR, SPEC], ... }`（OR）。

---

## CFG-1-6: must_be_linked_from

<details><summary>⬡ CFG-1-6 · v0.1.0</summary>

```yaml
id: CFG-1-6
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-1
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
各ノード型に課す必須の被依存辺（node ← source 群）ルール群の実インスタンス。あるノードが下流から参照されていること（孤立・終端の穴の検出）を `node`・`source`・`activate_stage`・`severity`・`reason` で列挙する。同一 node の複数行は AND、source が配列なら OR（いずれか1本以上から辺を受ければよい）。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `must_be_linked_from:` 配下のルール行群。例＝`{ node: VAL, source: [SR], ... }`・`{ node: SPEC, source: [TD], activate_stage: verification, severity: warning }`。

---

## CFG-1-7: fnd_lifecycle

<details><summary>⬡ CFG-1-7 · v0.1.0</summary>

```yaml
id: CFG-1-7
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-2
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
FND ノードの状態（未解消／resolved）に応じて必須辺の向きを逆転させるライフサイクルルールの実インスタンス。`resolved_field` で機械判定フィールド名を指定し、未解消時は forward 辺（FND → 対象）を必須、resolved 時は backward 辺（対象 → FND）を必須かつ forward 辺の不在を期待する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `fnd_lifecycle:` 配下。`resolved_field: resolved`・`unresolved.must_link_to`（target: any・severity error）・`resolved.must_be_linked_from`（source: any・error）・`resolved.must_not_link_to`（target: any・warning）。

---

## CFG-1-8: decision_spine

<details><summary>⬡ CFG-1-8 · v0.1.0</summary>

```yaml
id: CFG-1-8
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-2
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
DD / Q / PEND の決定スパイン義務辺ルールの実インスタンス。これらのノードから対象への辺が存在する＝反映未完了を意味し、反映後に辺を削除して逆向き（X → DD）に張り替える運用を機械検査する。義務辺にも ref_version が必須。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `decision_spine:` 配下。`{ node: DD, rule: RULE-001, severity: error }`・`{ node: Q, rule: RULE-002, severity: warning }`・`{ node: PEND, rule: RULE-022, severity: warning }`。

---

## CFG-1-9: rule_activation

<details><summary>⬡ CFG-1-9 · v0.1.0</summary>

```yaml
id: CFG-1-9
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
属性検査ルール（接続辺以外の RULE）ごとに、発火を開始するステージを定義する写像。current_stage が指定ステージ未満の間は当該ルールを発火させない（段階ゲート）。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `rule_activation:` 配下。`RULE-016/017/018: requirements`（condition 属性・FR カバレッジ系）・`RULE-019/020/021: verification`（TD↔SPEC 不一致・TR result/log_ref 欠落）。

---

## CFG-1-10: condition_vocab

<details><summary>⬡ CFG-1-10 · v0.1.0</summary>

```yaml
id: CFG-1-10
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
SPEC・TD の `condition` 属性が取りうる語彙（等価分割クラス）の許容集合。RULE-016 がこの語彙外の値を違反として検出する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `condition_vocab: [normal, boundary, empty, failure, error]`。normal＝ハッピーパス、boundary＝境界値、empty＝空集合/null（boundary と独立）、failure＝仕様違反を正しく検出する sad-path、error＝ツール自身が処理不能な異常入力（fail-close 対象）。

---

## CFG-1-11: coverage_rules

<details><summary>⬡ CFG-1-11 · v0.1.0</summary>

```yaml
id: CFG-1-11
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
ノード型ごとに、その配下 SPEC が満たすべき condition の必須・推奨集合を定義するカバレッジ要件の実インスタンス。RULE-017（required 欠落＝WARNING）・RULE-018（recommended 欠落＝WARNING）の判定基準となる。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `coverage_rules:` 配下。`FR.required_conditions: [normal]`・`FR.recommended_conditions: [failure, error]`。

---

## CFG-1-12: always_error

<details><summary>⬡ CFG-1-12 · v0.1.0</summary>

```yaml
id: CFG-1-12
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
いかなる抑制機構（scheduled / suppress / activate_stage）によっても抑制できない RULE の一覧。グラフ整合性の根幹に関わるため常に error として発火させる fail-close 指定。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `always_error: [RULE-005, RULE-007]`。RULE-005＝完全孤立（in/out 辺が0本）、RULE-007＝存在しない ID 参照。

---

## CFG-1-13: trace_scope

<details><summary>⬡ CFG-1-13 · v0.1.0</summary>

```yaml
id: CFG-1-13
type: CFG
labels: []
scheduled: ""
suppress: []
edges:
  - to: SCM-2-3
    ref_version: "0.1"
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

# CFG
検証ツールがトレース（ノード抽出・整合検査）の対象とするファイル集合を、include / exclude の glob パターンで画定する実インスタンス。exclude されたファイルは out-of-graph 扱いとなりノードを持たない。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `trace_scope:` 配下。`include: ["doc-system/**/*.md"]`・`exclude: ["docs/**", "**/README.md", "**/00-dashboard.md", "**/00-dfd.md"]`（ダッシュボードと DFD 図はノード非対象）。

---

## PROMPT（プロンプト）

## PROMPT-1: requirements-author 著作支援プロンプト（VAL/SR/FR/NFR）

<details><summary>⬡ PROMPT-1 · v0.1.0</summary>

```yaml
id: PROMPT-1
type: PROMPT
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

# PROMPT
要求層ノード（VAL / SR / FR / NFR）の著作支援プロンプト。外部ファイル参照なしに type 値・id PREFIX・必須辺方向・本文4項目・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/requirements-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の VAL/SR/FR/NFR を、type 値（VAL|SR|FR|NFR・自由記述不可）・id PREFIX（`VAL-`/`SR-`/`FR-`/`NFR-`・既存最大+1）・必須依存辺方向（SR→VAL・FR→SR・NFR→SR の無名依存辺）・本文4項目フォーマット・RULE チェックリスト（RULE-005/006/017/018）を**プロンプト内に閉じて**提供し、外部参照なしに著作させる（SPEC-27-1〜5）。
**入力変数**: `parent_id`（親ノード ID）／`parent_body`（親の本文・YAML）／`sprint`（current_phase）／`context`（関連ノード）／`error`（再試行時の差し戻し）。記載内容（I-9）＝各型の本文4項目（VAL＝便益1文・SR＝ステークホルダー欲求・FR＝機能1文・NFR＝制約）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子ノード群の Markdown（フロントマター YAML＋本文）を Write する＝tmp ノード草案（D-8）。本ファイルへは書かない（reconciliation 専権）。
**注意事項**: 辺は無名依存辺（kind/status を書かない・to は単数・ref_version 必須）。`scheduled: ""`（空文字のみ・将来フェーズは labels に post-mvp 等）。suppress 使用時は inline comment に理由必須（RULE-007 は抑制不可）。NFR の検証証跡辺は verification 発火のため requirements では沈黙（suppress 不要）。

---

## PROMPT-2: spec-author 著作支援プロンプト（SPEC・1アサーション1ノード）

<details><summary>⬡ PROMPT-2 · v0.1.0</summary>

```yaml
id: PROMPT-2
type: PROMPT
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

# PROMPT
SPEC ノードの著作支援プロンプト。外部ファイル参照なしに type 値・id 枝番パターン・必須辺方向・本文3項目・分割／RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/spec-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親 SPEC または FR 配下の子 SPEC を、type 値（SPEC・自由記述不可）・id 枝番（`親ID-N`・数字のみ・`-a/-b` 禁止）・必須依存辺方向（子→親 SPEC の無名依存辺・FR を直接参照しない）・本文3項目（前提条件／入力・トリガ／期待動作）・分割基準（1 SPEC=1 検証アサーション。複数 RULE・複数期待結果・複数トリガなら分割）・RULE チェックリスト（RULE-007/016/019）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`（親 SPEC/FR の ID）／`parent_body`／`sprint`／`context`（上流 FR・隣接 SPEC）／`error`。記載内容（I-9）＝各子 SPEC の3項目本文＋`condition`（normal|boundary|empty|failure|error・RULE-016 ERROR）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子 SPEC 群＋更新後の親 YAML を Write する＝tmp ノード草案（D-8）。既存ファイルは上書き（再試行も同様）。本ファイルへは書かない。
**注意事項**: 親→子の辺は持たない（階層は ID パターン `X-N` で表現）。辺は無名依存辺（kind/status なし・to は単数・ref_version 必須）。`scheduled: ""` 固定（`verification`/`sprint-N` 禁止）。全子に `condition` 属性必須。SPEC←TD 被依存辺は verification 発火のため沈黙（ノード suppress を付けない）。

---

## PROMPT-3: analysis-author 著作支援プロンプト（ACTOR/I/O/D/P/E）

<details><summary>⬡ PROMPT-3 · v0.1.0</summary>

```yaml
id: PROMPT-3
type: PROMPT
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

# PROMPT
分析層ノード（ACTOR / I / O / D / P / E）の著作支援プロンプト。外部ファイル参照なしに type 値・id PREFIX・必須辺方向・本文フォーマット・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/analysis-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の ACTOR/I/O/D/P/E を、type 値（自由記述不可）・id PREFIX（`ACTOR-`/`I-`/`O-`/`D-`/`P-`/`E-`・退役 ID 再利用禁止）・必須依存辺方向（依存方向に統一・DD-017＝ACTOR→SR・I→SPEC・O→SPEC/P/ACTOR・D→SPEC/P・P→SPEC（・I/D/E 該当時）・E→SPEC/ACTOR）・各型本文フォーマット（E は5要素必須）・RULE チェックリスト（RULE-005/006）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`／`parent_body`／`sprint`／`context`／`error`。記載内容（I-9）＝各型の本文（I/O＝もの・発生源/受け手・形式・タイミング、P＝単一責務1文＋入出力/トリガ辺、E＝スティミュラス/アクション/レスポンス/アフェクト/イベント名の5要素）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子ノード群の Markdown を Write する＝tmp ノード草案（D-8）。本ファイルへは書かない。
**注意事項**: 辺方向は依存方向（O→P・P→E・O/E→ACTOR）。プロセス間中間データは D 型で必ず起票（O→ACTOR を持たない・DD-7）し価値経路（PR6）を連続させる。辺は無名依存辺（kind/status なし・to は単数・ref_version 必須）。E は刺激元 `→ACTOR` 必須（DD-020）。`scheduled: ""` 固定。

---

## PROMPT-4: design-author 著作支援プロンプト（ORC/DS/MOD/DM/PORT/PRS/SCM/CFG/PROMPT/TERM）

<details><summary>⬡ PROMPT-4 · v0.1.0</summary>

```yaml
id: PROMPT-4
type: PROMPT
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

# PROMPT
設計層ノード（ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM）の著作支援プロンプト。外部ファイル参照なしに type 値・id PREFIX・必須辺方向・本文フォーマット・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/design-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の設計層10型を、type 値（自由記述不可）・id PREFIX（`MOD-`/`PORT-`/`PRS-`/`DS-`/`ORC-`/`DM-`/`TERM-`/`SCM-`/`CFG-`/`PROMPT-`）・必須依存辺方向（MOD→P|D・PORT→MOD・PRS→DS・DS→P・ORC→E・DM→TERM/MOD・TERM→SPEC・SCM→SPEC・CFG→SCM/SPEC・PROMPT→SPEC）・各型本文フォーマット・RULE チェックリスト（RULE-006/007）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`／`parent_body`／`sprint`／`context`／`error`。記載内容（I-9）＝各型本文（MOD＝責務1文+公開I/F+依存、PORT＝抽象化する副作用、PRS/DS＝保存対象・理由・ライフサイクル、ORC＝制御フロー+失敗経路、DM＝定義+型+不変条件、SCM＝目的+フォーマット+必須フィールド、CFG＝用途+ファイルパス、PROMPT＝目的+版+入力変数、TERM＝定義）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子ノード群の Markdown を Write する＝tmp ノード草案（D-8）。本ファイルへは書かない。
**注意事項**: 辺は無名依存辺（旧 kind refines/instantiates/uses/see-also は廃止・to は単数・ref_version 必須）。SCM/CFG/PROMPT の階層は -N 採番で表現（自己辺ルールが無いため親子辺は張らない）。`scheduled: ""` 固定。RULE-007 は抑制不可。

---

## PROMPT-5: verification-author 著作支援プロンプト（TD/TC/TR/VERIFY/FND/DD/Q/PEND）

<details><summary>⬡ PROMPT-5 · v0.1.0</summary>

```yaml
id: PROMPT-5
type: PROMPT
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

# PROMPT
検証層・意思決定ノード（TD / TC / TR / VERIFY / FND / DD / Q / PEND）の著作支援プロンプト。外部ファイル参照なしに type 値・id PREFIX・必須辺方向・追加属性・本文フォーマット・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/verification-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の検証・意思決定ノードを、type 値（自由記述不可）・id PREFIX（`TD-`/`TC-`/`TR-`/`VERIFY-`/`FND-`/`DD-`/`Q-`/`PEND-`）・必須依存辺方向（TD→SPEC・TC→TD・TR→TC・VERIFY→any・FND は状態で逆転・DD/Q/PEND→影響要素の義務辺）・追加属性（TD の condition＝SPEC と一致／TR の result・log_ref／FND の resolved）・RULE チェックリスト（RULE-016/019/020/021/001/002/022 とライフサイクル）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`／`parent_body`／`sprint`／`context`／`error`。記載内容（I-9）＝各型本文＋メタ属性（TD＝condition、TR＝result/log_ref、FND＝resolved＋指摘時 ref_version の本文記録＝DD-3、DD/Q/PEND＝ライフサイクル状態を本文見出し/バッジに記載）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子ノード群の Markdown を Write する＝tmp ノード草案（D-8）。本ファイルへは書かない。
**注意事項**: 辺は無名依存辺（kind/status なし・to は単数・ref_version 必須）。FND は状態で辺逆転（未解消＝forward `FND→対象`／resolved＝backward `対象→FND`＋forward 削除＋本文に指摘時 ref_version を凍結＝DD-3）。DD/Q/PEND の義務辺は反映後 `DD→X` を削除し `X→DD` に置換。接続規則変更を伴う DD/FND は対応 author/スキル/接続マトリクスへ同期（FND-99 パターン）。`scheduled: ""` 固定・RULE-007 抑制不可。

---

## PROMPT-6: reconciliation 調停支援プロンプト（検証＋本ファイル転記）

<details><summary>⬡ PROMPT-6 · v0.1.0</summary>

```yaml
id: PROMPT-6
type: PROMPT
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-39
    ref_version: "0.1"
```
</details>

# PROMPT
著作出力（tmp ノード草案）に対する**調停プロンプト**。草案スキーマの検証機能（P-7-2-1）に加え、検証合格後に草案を本ファイルへ転記する調停機能（P-7-2-2 本ファイル転記）を併せ持つため PROMPT 化する（オーナー指示）。SPEC-39 の実体＝`.claude/agents/reconciliation.md`。
**バージョン**: 1.0
**目的**: (1) 検証＝reconciliation-validator が返した VALIDATION_OK ブロック（validated・self_fix）を前提に、id 欠如・ref_version 不一致・残存 kind/status・to のリスト記法・resolved FND の元 forward 辺残存等の確定修正を tmp 上で適用する（検証ロジックは再実装せず validator 判定を信頼＝P-7-2-1）。(2) 調停＝self_fix 適用後の草案を `doc-system/` または `docs/` 配下の本ファイルへ Write/Edit で確定転記し、全書込完了後に tmp を掃除する（P-7-2-2 本ファイル転記）。id 欠如等の構造違反検出時は転記を中断し主文脈へ差し戻す（SPEC-39 系列・fail-close）。
**入力変数**: `sprint`（current_phase）／`validation_ok`（validator の VALIDATION_OK ブロック＝validated・self_fix。記載内容 I-9）。`validation_ok` 欠如・ROLLBACK 含みは書込せずエラー返却。
**出力形式**: 本ファイル（`doc-system/`・`docs/` 配下）への確定書き込み（D-8 草案の正本反映）＋ `tmp/<sprint>/` の掃除。完了報告は DONE ブロック（layer/sprint/written/applied_self_fix）。
**注意事項**: 検証前（validation_ok 無し）・ROLLBACK 含み・self_fix 適用不能のいずれも書込せず主文脈へ返す（fail-close）。Bash は `python3 -m docidx`（書込位置特定）と `python3 -m backref`（FND 辺逆転の機械実行）専用、それ以外の本文編集は Write/Edit のみ（場当たり sed/awk/echo 禁止）。検証ロジックは再実装しない（validator 専権・二重実装ドリフト防止）。

---

## PROMPT-7: reconciliation-validator 検証支援プロンプト（read-only 構造検証・VALIDATION_OK/ROLLBACK）

<details><summary>⬡ PROMPT-7 · v0.1.0</summary>

```yaml
id: PROMPT-7
type: PROMPT
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-39
    ref_version: "0.1"
```
</details>

# PROMPT
著作出力（tmp ノード草案）に対する**read-only 構造検証プロンプト**。草案スキーマ検証（P-7-2-1）を実装する LLM エージェント reconciliation-validator のシステムプロンプトで、合格なら `VALIDATION_OK`（自己修正可フラグ `self_fix` 付き）、不合格なら `ROLLBACK` を返す。書込ツールを構造的に持たないことで検証段の fail-close を保証する（DD-22）。SPEC-39 の検証挙動（id 欠如検出→エラー報告→転記中断）の検証フェーズ（P-7-2-1）を担い、書込専任の reconciliation（PROMPT-6・P-7-2-2）と責務分離する。SPEC-39 の検証側実体＝`.claude/agents/reconciliation-validator.md`。
**バージョン**: 1.0
**目的**: tmp 草案を **read-only で構造検証**し判定を返す。(1) 合成グラフ構築＝本ファイルを丸読みせず tmp 参照 ID とその周辺ノードだけを docidx CLI で surgical read して合成する。(2) 整合性検証＝edges.to 実在（RULE-007 always_error）・id 一意・階層 ID `X-N` の親存在（RULE-008）・子→親依存辺・辺の無名性（kind/status なし・to 単数）・ref_version の参照先バッジ x.y 一致（RULE-004）・型別属性（SPEC の condition/単一アサーション・TD の condition 一致・TR の result/log_ref）・resolved FND の辺逆転（backref 付与・元 forward 辺削除）を全件チェックする。(3) 判定生成＝内容問題（存在しない ID 参照・SPEC 分割粒度違反・FND backref 未付与等）は `ROLLBACK`、自己修正可の不整合は確定修正指示として `self_fix` に列挙した `VALIDATION_OK` を返す。**ファイルは一切書かない**（書込は reconciliation の専権）。
**入力変数**: `sprint`（current_phase）／`parent_ids`（今回の著作対象の親ノード ID リスト）／`layer`（requirements / spec / analysis / design / verification。確認対象の読込範囲を絞る）。sprint 未指定なら config.yaml の current_phase を取得。
**出力形式**: 判定ブロックの返却のみ（ファイル書込なし）。合格＝`VALIDATION_OK`（layer・sprint・validated・self_fix。self_fix は target・field・action の確定修正指示）。不合格＝`ROLLBACK`（parent_id・agent・errors）。Bash は `python3 -m docidx`（ノード検索/読み込み）専用。
**注意事項**: ファイルは一切書かない（tmp も本ファイルも）＝バグや誤判定でも構造的に本ファイルへ書けない fail-close（DD-22）。自己修正を自分で適用せず、参照先から読み取った確定値を `self_fix` に指示として載せ writer に渡す（曖昧指示禁止）。読込は surgical read を徹底し本ファイル丸読みは docidx で解決できない構造確認に限る。RULE-007 は always_error（抑制不可）→ROLLBACK。検証ロジックは reconciliation 側と二重実装せず本プロンプト（validator）に集約する。矛盾・判断必須は ROLLBACK で打ち上げ勝手に解消しない（PR7・原案/理由を errors に添える＝意見なき停止禁止）。
