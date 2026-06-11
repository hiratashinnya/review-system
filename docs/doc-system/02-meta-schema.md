# メタ属性スキーマ

> ファイル版・ノード・エッジが持つ属性の定義。
> 埋め込み記法（`<details>` トグル）は [04](04-notation.md) で確定。

---

## 1. ファイルバージョニング

バージョン管理の単位は**ファイル**。各 Markdown ファイルの frontmatter に記載する。

```yaml
---
doc_title: クラス設計
version: "1.2.0"
---
```

### バージョン桁の意味

| 桁 | 変化の意味 | エッジへの影響 |
|---|---|---|
| **x（メジャー）** | 構造破壊（要素の追加/削除/型変更） | `ref_version` の `x.y` 不一致 → RULE-004 ERROR |
| **y（マイナー）** | 有意な内容変更（仕様変更・新規記述） | 同上 |
| **z（パッチ）** | 誤字修正・表現調整のみ | **無視**（`x.y` で比較・z は問わない） |

> **ファイル単位の粒度について**：ファイル内の1ノードが変化するとそのファイルへの全辺が pending になる。
> これはファイルをコンセプト単位で小さく保つことで許容できる。1ファイル＝1責務が設計原則。

---

## 2. ノード属性スキーマ

```yaml
id:        string     # 必須：グローバル一意・永続。PREFIX-N[-N...]（§3）
type:      string     # 必須：要素型（§6）
labels:    [string]   # 任意：任意の分類タグ（例: [post-mvp, experimental, deprecated]）
scheduled: string     # 任意：対応予定フェーズ（config.yaml の phases リストの値）
                      # current_phase より後のフェーズが指定された場合、
                      # このノードに対するルールを完全サイレント（RULE-007 のみ除外）
condition: string     # SPEC/TD のみ推奨。テスト条件分類（§2a 参照）。
                      # 省略時は RULE-016 で WARNING。
suppress:  [string]   # 任意：このノードで抑制するルール番号のリスト（§8 suppress 抑制参照）
                      # 抑制理由は本文または inline comment に必ず記載する。
                      # always_error ルール（RULE-007）は suppress 対象外。

# TR 専用属性（type: TR のノードにのみ付与）
result:    string     # TR のみ：PASS | FAIL（RULE-020。省略時 WARNING）
log_ref:   string     # TR のみ：ログファイルのパスまたは URL
                      # result: FAIL のとき log_ref がないと RULE-021 で WARNING
```

> **ライフサイクル状態（DD/Q/PEND）はメタ属性に持たない**。本文の見出しや
> バッジ（`**status: decided**`）に記載する。理由：ライフサイクルは人が読む情報であり、
> 機械が状態を読む必要があれば本文パースで取得できる。

> **バージョンはノードに持たない**。ファイル単位で管理（§1）。

---

## 2a. condition 属性（SPEC・TD 専用）

> **目的**：テスト条件種別を機械可読にして、FR ごとの仕様カバレッジを条件軸で検証する。
> **適用型**：`SPEC`・`TD`（それ以外に付与しても無視）

### 語彙（config.yaml の `condition_vocab` で拡張可能）

| 値 | 意味 | 分けるべき理由 |
|---|---|---|
| `normal` | 正常系：有効な入力・正常な状態 → 期待通りに動く | すべての FR に必須（RULE-017）。仕様の核心 |
| `boundary` | 境界値：有効/無効の境目にある入力・状態 | バグが集中する。`normal` とも `failure` とも別コードパスになることが多い |
| `failure` | 不成立：無効な入力・業務ルール違反 → 拒否応答 | バリデーション・ガード節のロジックを検証。`error` とは実装レベルで別 |
| `error` | 異常：インフラ障害・タイムアウト・予期しない例外 → フェイルセーフ | try/catch・サーキットブレーカー・ロールバックを検証。`failure` とは別コードパス |

> 語彙は `config.yaml` の `condition_vocab` で拡張できる。プロジェクト固有の条件を追加可能。

### TD の condition は SPEC と一致させる

`TD` の `condition` は `verifies` 辺で指す `SPEC` の `condition` と一致させることを推奨。
不一致は RULE-019 で WARNING（「boundary SPEC を normal TD でテストしている」等の設計ミスを検出）。

### カバレッジ検証のイメージ

```
FR-001
  ├─ SPEC-001  condition: normal   ← TD-001 ✅
  ├─ SPEC-002  condition: boundary ← TD-002 ✅
  ├─ SPEC-003  condition: failure  ← TD-003 ✅
  └─ SPEC-004  condition: error    ← ⚠️ TD なし（RULE-015 発火）
```

RULE-017: FR に `condition: normal` の SPEC がなければ WARNING（正常系未定義）。
RULE-018: FR に `condition: failure` も `condition: error` もなければ INFO（負例未考慮）。

---

## 3. ID 体系

### 形式

```
PREFIX-N[-N[-N...]]
```

- `PREFIX` = 要素型に対応する大文字略称（§6 参照）
- `N` = 連番（1から始まる整数。ゼロ埋め不要）
- 階層化：`-N` を追加することで親子関係を表現

### 階層 ID の例

```
I-1          # 入力1（親）
I-1-1        # 入力1の子1（I-1 を分割）
I-1-2        # 入力1の子2
I-1-1-1      # 入力1-1 のさらに詳細

P-3          # プロセス3
P-3-1        # プロセス3の子プロセス1
P-3-2        # プロセス3の子プロセス2
```

### 規則

- id は**永続**：要素をリネームしても id は変えない。意味は heading が持つ。
- 階層は **ID パターン `X-N` から推論**する（`decomposes` 辺は廃止・DD-014）。
  子 `I-1-1` が存在すれば親 `I-1` の存在を検証する（RULE-008）。
- doc-system 自身の意思決定も同じ id 空間（`DD-001`, `Q-001` など）。

---

## 4. エッジ属性スキーマ

```yaml
edges:
  - to:          string   # 必須：参照先ノード id（単数のみ・リスト禁止）
    ref_version: string   # 必須：参照先ファイルの x.y（ドリフト検出に使用）
    note:        string   # 任意：補足・理由
```

- **`kind` フィールドは存在しない**（DD-012）。辺は無名の依存辺であり、関係の名称は
  グラフ走査時に `(source 型, target 型)` から読み取る（接続マトリクス [03](03-connection-matrix.md)）。
- **`status` フィールドは存在しない**（DD-013）。ドリフトは `ref_version` 比較が唯一の真実源（§7）。
- **`to` はスカラー string のみ**。複数先へ依存する場合は辺を分割して1辺1 `to` で書く。

```yaml
edges:
  # 1辺1 to（複数依存は辺を分割）
  - to: SR-003
    ref_version: "1.2"
  - to: VAL-001
    ref_version: "2.0"
    note: "派生元の価値命題"
```

---

## 5. エッジの意味論（無名依存辺）

辺は1種類だけ：**依存辺**。

> **`A → B` ＝ 「A は B に依存する」＝「B が変われば A は見直しが必要」。**

- 辺に種別ラベル（kind）は持たせない。関係の名称（refines / realizes / verifies …）は
  `(source 型, target 型)` の組から一意に読み取れるため、冗長な記録をしない（DD-012）。
- **依存方向に統一**（DD-017）：辺は常に「自分が影響を受ける先」を指す。
  - `O → P`：出力は生成プロセスに依存（旧 `P → O produces` を反転）
  - `P → E`：プロセスはトリガ事象に依存（旧 `E → P triggers` を反転）
  - `P → I`：プロセスは入力に依存（消費）
  - `O → ACTOR`：出力は受け手アクタに依存／`E → ACTOR`：事象は刺激元アクタに依存
- **唯一の例外＝決定スパインの義務辺**（DD-016）。`DD/Q/PEND → X` は「この決定が X に
  影響する（反映が要る）」を表す一時辺で、依存方向とは**逆向き**。識別は **source 型が
  DD/Q/PEND かどうか**で行う（§7・§9 グループ A）。

### 廃止した関係（DD-014）

| 旧 kind | 廃止理由 | 代替 |
|---|---|---|
| `see-also` | 参照＝依存。影響がなければ辺を張らない | 依存辺（影響があるなら普通の辺） |
| `replaces` | 歴史情報でありドリフト対象にすべきでない | 本文更新＋ファイル版 bump |
| `extends` | 実使用ゼロ | 無名依存辺（子→親） |
| `contradicts` | 方向性のない観測＝指摘 | FND（`FND→A` と `FND→B` の2辺） |
| `decomposes` | 階層は ID パターン `X-N` から推論可能 | ID パターン（§3・RULE-008） |

> `refines`/`realizes`/`instantiates`/`verifies`/`validates`/`found-in`/`consumes`/`produces`/
> `triggers`/`constrains`/`uses`/`produced-by` 等の旧 kind は、**すべて無名依存辺**になった。
> 名称が要るときは型ペアから読む。

---

## 6. 要素型（type）一覧

| 型値 | ID接頭辞 | 層 | 説明 |
|---|---|---|---|
| `VAL` | `VAL-` | Why | 価値命題 |
| `SR` | `SR-` | Why | ステークホルダー要求 |
| `FR` | `FR-` | What | 機能要求 |
| `SPEC` | `SPEC-` | What | 機能仕様（テスタブル粒度） |
| `NFR` | `NFR-` | What | 非機能・制約 |
| `TERM` | `TERM-` | 共有語彙 | 用語・データ辞書エントリ |
| `ACTOR` | `ACTOR-` | 分析 | 外部アクタ |
| `I` | `I-` | 分析 | 入力（系外アクタ発） |
| `O` | `O-` | 分析 | 出力（系外アクタ宛） |
| `D` | `D-` | 分析 | 内部データフロー（プロセス間・系外へ出ない） |
| `P` | `P-` | 分析 | 論理プロセス |
| `E` | `E-` | 分析 | イベント |
| `ORC` | `ORC-` | 設計・振る舞い | オーケストレーション段 |
| `DS` | `DS-` | 設計・振る舞い | 状態・データストア |
| `MOD` | `MOD-` | 設計・静的 | モジュール |
| `DM` | `DM-` | 設計・静的 | ドメイン型 |
| `PORT` | `PORT-` | 設計・静的 | ポート・アダプタ |
| `PRS` | `PRS-` | 設計・静的 | 永続設計 |
| `SCM` | `SCM-` | 設計・静的 | スキーマ |
| `CFG` | `CFG-` | 設計・静的 | コンフィグ |
| `PROMPT` | `PROMPT-` | 設計・静的 | プロンプトテンプレート |
| `TD` | `TD-` | 検証 | テスト設計 |
| `TC` | `TC-` | 検証 | テストコード |
| `TR` | `TR-` | 検証 | テスト結果 |
| `VERIFY` | `VERIFY-` | 検証 | ドキュメント検証実施 |
| `FND` | `FND-` | 検証 | 指摘・finding |
| `DD` | `DD-` | 横断 | 意思決定 |
| `Q` | `Q-` | 横断 | 未決論点 |
| `PEND` | `PEND-` | 横断 | 先送り論点 |

---

## 7. ドリフト検出（ref_version が唯一の真実源）

`status` フィールドは廃止した（DD-013）。辺がドリフトしているかは **`ref_version` 比較**だけで決まる。

### バージョンドリフト（RULE-004）

```
edge.ref_version の x.y ≠ 参照先ファイルの現在 version の x.y
  → ドリフト = ERROR（検証ツールが検出・報告）
```

- 上流が x.y を上げたら、依存辺の `ref_version` は古いままになり ERROR で表面化する。
- **見直して影響を取り込んだら（または影響なしと判断したら）、`ref_version` を現在版に
  素直に更新する**。これが「反映済み」の唯一の表現（旧 `done`/`n/a` 概念は不要）。

### 意思決定ドリフト（RULE-001/002/022）— 義務辺モデル

```
DD/Q/PEND → X の辺が「存在する」 = その決定が X にまだ反映されていない
  DD→X 存在  → RULE-001 ERROR
  Q→X 存在   → RULE-002 WARNING
  PEND→X 存在 → RULE-022 WARNING
```

- 反映が完了したら **`DD→X` 辺を削除し、`X→DD` の依存辺を新たに張る**（DD-016）。
  これにより「未反映 = 義務辺の存在」「反映済 = 逆向き依存辺」が構造で表現され、status を持たない。
- 義務辺にも `ref_version` は必須。反映前に X が別件で更新されたら義務辺がドリフト ERROR になり、
  「その決定は古い X を前提にしている。見直せ」のシグナルになる（DD-015）。
- DD/Q/PEND の判定は **ノードの型**で行う。lifecycle 状態（decided/open）の本文パースは不要。

---

## 8. ルール抑制仕様

> 設定ファイル：`docs/doc-system/config.yaml`

### 抑制の3軸

| 軸 | 設定 | 条件 | 効果 |
|---|---|---|---|
| **scheduled 抑制** | ノード属性 `scheduled` | `scheduled` のフェーズが `current_phase` より後 | **完全サイレント**（ルール非発火） |
| **ステージ発火** | `config.yaml` の `must_link_to`/`must_be_linked_from` 行の `activate_stage`・属性ルールの `rule_activation` | `current_stage` が発火ステージ未満 | **未到達ルールは沈黙**（旧 `stage_scope.disable` マトリクスを代替） |
| **suppress 抑制** | ノード属性 `suppress` | ルール番号がリストに含まれる | **完全サイレント**（そのルールのみ非発火）。`always_error` ルールは無効 |

> **suppress と labels の違い**：`labels` は人向けの分類タグ（機械が意味を解釈しない）。
> `suppress` はルール番号を指定する機械向け専用属性。分類目的には使わない。

### scheduled 抑制の判定

```
phases リストのインデックス比較：
  index(node.scheduled) > index(current_phase)
    → このノードに関するルールは全て発火しない

例：
  phases: [sprint-1, sprint-2, sprint-3, post-mvp]
  current_phase: sprint-1
  node.scheduled: sprint-2
  → index(sprint-2)=1 > index(sprint-1)=0 → 完全サイレント
```

### ステージ発火の判定

```
# 接続ルール（RULE-006）
must_link_to / must_be_linked_from の各行は activate_stage を持つ
  index(current_stage) < index(row.activate_stage)
    → その行の接続要求は発火しない（沈黙）

# 属性ルール（RULE-016〜021）
rule_activation[RULE-x] が発火開始ステージを定義
  index(current_stage) < index(rule_activation[RULE-x])
    → ルール R は発火しない（沈黙）

current_stage が stages リストに存在しない
  → 全ルールを元の深刻度で評価する（ツール設定エラーを報告）
```

### suppress 抑制の判定

```
node.suppress にルール番号 R が含まれる
  → そのノードに対する R の発火をスキップ

例：
  suppress: [RULE-018]   # error path が存在しない設計（外部システムは常時稼働前提）
  → RULE-018 はこのノードに対して発火しない
```

> suppress 記載時は**理由を inline comment または本文に必ず残す**。
> 理由なき suppress は将来の読者が判断できず、PR レビューで拒否することを推奨（運用ルール）。

### suppress の記述例

```yaml
suppress: [RULE-018]   # error path なし: 呼び出し元がインフラ保護済みの内部 API
```

```yaml
suppress:
  - RULE-018   # error path なし: 外部システムは常時稼働前提（SLA 99.99%）
  - RULE-016   # condition 不要: このノードは手動確認のみで TD を持たない設計
```

### 抑制の例外

**always_error ルール（RULE-007 等）は suppress 対象外**。  
scheduled/stage/suppress いずれの方法でも抑制不可。存在しない ID を参照している時点でグラフが壊れており、フェーズや設計意図を問わず常に ERROR。

### config.yaml の構造

```yaml
# docs/doc-system/config.yaml（抜粋）

current_phase: "sprint-1"
current_stage: "requirements"

phases: [sprint-1, sprint-2, sprint-3, post-mvp]
stages: [requirements, analysis, design, implementation, verification]

# 必須接続①：依存辺（node → target）。同一 node の複数行 = AND・target 配列 = OR
must_link_to:
  - { node: SPEC, target: FR,   activate_stage: requirements, severity: error,   reason: "SPECはFRを詳細化" }
  - { node: O,    target: P,    activate_stage: analysis,     severity: error,   reason: "出力は生成プロセスに依存（O→P）" }
  - { node: TD,   target: SPEC, activate_stage: verification, severity: error,   reason: "TDは仕様を検証" }
  # …（全行は config.yaml 本体を参照）

# 必須接続②：被依存辺（node ← source 群）。source 配列 = OR
must_be_linked_from:
  - { node: SPEC, source: [TD],              activate_stage: verification, severity: warning, reason: "仕様はテスト設計で覆われる" }
  - { node: NFR,  source: [FND, TC, VERIFY], activate_stage: verification, severity: warning, reason: "NFRは検証証跡を受ける" }
  # …

# 決定スパイン（source 型で判定）
decision_spine:
  - { node: DD,   rule: RULE-001, severity: error }
  - { node: Q,    rule: RULE-002, severity: warning }
  - { node: PEND, rule: RULE-022, severity: warning }

# 属性ルールの発火開始ステージ（旧 stage_scope.disable を代替）
rule_activation:
  RULE-016: requirements   # condition 属性なし（ERROR）
  RULE-020: verification   # TR result なし（ERROR）
  RULE-021: verification   # TR log_ref なし（ERROR）

always_error:
  - RULE-005   # 完全孤立（抑制不可）
  - RULE-007   # 存在しない ID 参照（抑制不可）
```

---

## 9. ドリフト検出・検証ルール

> 検証ツールが走査するルールの完全定義。
> 深刻度：**ERROR**（必ず解消）／**WARNING**（要確認・合理的な理由があれば n/a 許容）／**INFO**（記録のみ）

### グループ A：意思決定ドリフト（義務辺モデル）

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-001** | `DD` ノード | `DD→X` の義務辺が存在する（＝未反映） | **ERROR** | `DD-015 → DM-001 が未反映（義務辺が残存）` |
| **RULE-002** | `Q` ノード | `Q→X` の義務辺が存在する | **WARNING** | `Q-003 → FR-007 が未追跡（未決論点の影響候補）` |
| **RULE-022** | `PEND` ノード | `PEND→X` の義務辺が存在する | **WARNING** | `PEND-002 → FR-009 が先送り中（影響候補）` |

> **型で判定**：ノード型が DD/Q/PEND なら、その out 辺は義務辺。辺の**存在そのもの**が未反映を意味する。
> 反映完了で **`DD→X` を削除し `X→DD`（依存辺）を追加**する（DD-016）。status は持たない。

---

### グループ B：バージョンドリフト

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| ~~RULE-003~~ | — | **廃止**（RULE-004 に統合・ドリフトは一律 ERROR） | — | — |
| **RULE-004** | `ref_version` を持つ**全辺**（義務辺含む） | `ref_version` の x.y ≠ 参照先ファイルの現在 version の x.y | **ERROR** | `DM-001 → TERM-003 の ref_version 1.2 が古い（現: 1.4.0）` |

> see-also 廃止により辺は全て依存辺。依存先の更新確認は必須なので、ドリフトは一律 ERROR。

---

### グループ C：構造的な接続不足

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-005** | 全ノード | in/out 辺が **0 本**（完全孤立） | **ERROR（always_error）** | `I-3 が孤立している（辺が必要）` |
| **RULE-006** | config の `must_link_to`/`must_be_linked_from` 行 | 必須接続を満たさない | **行ごと**（error/warning） | `DM-005 に TERM への辺がない（must_link_to）` |
| **RULE-007** | 辺の `to` フィールド | 参照先 ID が存在しない | **ERROR（always_error）** | `辺 FR-009 → SR-999 の参照先 SR-999 が未定義` |
| **RULE-008** | 階層 ID（例: `I-1-1`） | 親ノード（`I-1`）が**存在しない** | **ERROR** | `I-1-1 の親 I-1 が存在しない（孤児階層）` |

> RULE-006 は設定駆動。旧 RULE-009/010/011/012/013/015 はすべてこの config 行に吸収された。
> 各行が自己説明的な `reason` と `severity` を持つ。
> RULE-008 は decomposes 辺の廃止に伴い「親ノードの存在チェック」へ転用（WARNING→ERROR 昇格）。

---

### グループ D：検証・指摘の完結性 → **RULE-006 に統合（廃止）**

| RULE# | 旧内容 | 後継 |
|---|---|---|
| ~~RULE-009~~ | FND に found-in/validates 辺が 0 本 | `must_link_to: FND→any` |
| ~~RULE-010~~ | FND に found-in 辺なし | （FND→any に統合） |
| ~~RULE-011~~ | NFR に validates 辺なし | `must_be_linked_from: NFR ← [FND,TC,VERIFY]` |
| ~~RULE-012~~ | TC に realizes 辺なし | `must_link_to: TC→TD` |
| ~~RULE-013~~ | VERIFY に verifies 辺なし | `must_link_to: VERIFY→any` |

---

### グループ E：see-also → **廃止**

| RULE# | 旧内容 | 後継 |
|---|---|---|
| ~~RULE-014~~ | see-also 辺に伝播ステータス | see-also 廃止（DD-014）。参照は依存辺で表す |

---

### グループ F：仕様カバレッジ

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| ~~RULE-015~~ | `SPEC` | TD からの verifies が 0 本 | **廃止** | → `must_be_linked_from: SPEC ← [TD]` |
| **RULE-016** | `SPEC`・`TD` | `condition` 属性がない | **ERROR** | `SPEC-002 に condition 属性がない` |
| **RULE-017** | `FR` | refines 先 SPEC 群に `condition: normal` がない | **WARNING** | `FR-005 に正常系仕様がない` |
| **RULE-018** | `FR` | refines 先 SPEC 群に `failure` も `error` もない | **WARNING** | `FR-005 に不成立・異常系の仕様がない（意図的なら suppress: [RULE-018]）` |
| **RULE-019** | `TD` | `condition` が verifies 先 SPEC の `condition` と不一致 | **WARNING** | `TD-003 (normal) が SPEC-002 (failure) を検証している` |

> RULE-016：condition が「無い」のは ERROR（未充足の RULE-017 とは別軸）。
> RULE-018：負例なしは INFO→WARNING に昇格（意図的なら suppress）。

---

### グループ G：テスト結果の完結性

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-020** | `TR` ノード | `result` 属性がない | **ERROR** | `TR-001 に result 属性がない（PASS/FAIL 不明）` |
| **RULE-021** | `TR` ノード | `log_ref` がない（**result 問わず**） | **ERROR** | `TR-001 に log_ref がない（証跡なき報告）` |

> ログはノード化しない方針のため、`log_ref` が唯一のエビデンス。PASS/FAIL を問わず証跡なき TR は ERROR。

---

### ルール一覧サマリ

| RULE# | グループ | 深刻度 | 一言説明 |
|---|---|---|---|
| RULE-001 | A | ERROR | DD の義務辺存在 = 反映漏れ |
| RULE-002 | A | WARNING | Q の義務辺存在 = 未追跡 |
| RULE-022 | A | WARNING | PEND の義務辺存在 = 先送り中 |
| ~~RULE-003~~ | B | — | 廃止（→ RULE-004） |
| RULE-004 | B | ERROR | 全依存辺の ref_version 不一致 |
| RULE-005 | C | ERROR（always） | 完全孤立（in/out 0 本） |
| RULE-006 | C | 行ごと | 必須接続の欠如（config 駆動） |
| RULE-007 | C | ERROR（always） | 存在しない ID への参照 |
| RULE-008 | C | ERROR | 階層 ID の親ノード不在 |
| ~~RULE-009〜013~~ | D | — | 廃止（→ RULE-006 config） |
| ~~RULE-014~~ | E | — | 廃止（see-also 廃止） |
| ~~RULE-015~~ | F | — | 廃止（→ RULE-006 config） |
| RULE-016 | F | ERROR | SPEC/TD に condition 属性なし |
| RULE-017 | F | WARNING | FR に condition: normal の SPEC がない |
| RULE-018 | F | WARNING | FR に failure/error の SPEC がない |
| RULE-019 | F | WARNING | TD の condition が SPEC と不一致 |
| RULE-020 | G | ERROR | TR に result 属性なし |
| RULE-021 | G | ERROR | TR に log_ref なし（result 問わず） |

---

## 9. 確定決定ログ

| DD# | 内容 |
|---|---|
| DD-001 | 可視性：`<details>/<summary>` を採用（GitHub ネイティブトグル）。stripped 版は後続オプション |
| DD-002 | ID 形式：連番（`PREFIX-N`）、永続。意味は heading が持つ。リネームで id を変えない |
| DD-003 | 直接の親（隣接1段）のみ必須（D2 旧「全祖先必須」を撤回）。SRC/TC も直接先のみ（D3） |
| DD-004 | バージョニング単位：ファイル単位（frontmatter `version: x.y.z`）。z は伝播判定に不問 |
| DD-005 | ライフサイクル状態はメタ属性に持たず本文に記載 |
| DD-006 | `mvp` 属性を廃止し `labels: [...]` で汎化 |
| DD-007 | `scheduled` 抑制＝完全サイレント（WARNING 降格ではない）。ステージ抑制＝ERROR→WARNING。RULE-007 のみ常に ERROR |
| DD-008 | USDM 分割：FR（機能要求・なぜ必要か）と SPEC（機能仕様・テスタブル粒度）を分離。分析層以降は SPEC を直接の親とする |
| DD-009 | テスト3層分離：TD（テスト設計・SPEC を verifies）→ TC（テストコード・TD を realizes）→ TR（テスト結果・TC を produced-by）。TD→SPEC の verifies 辺でカバレッジを機械検証（RULE-015） |
| DD-010 | `condition` 属性（旧 `scenario` をリネーム）。sub-ID 案を退け DD-002 原則を維持。語彙：normal/boundary/failure/error（config.yaml 拡張可）。`boundary` を独立させた理由：正常と失敗の境目は別コードパスになることが多く、テスト設計上も分離すべき。FR×condition×TD のカバレッジを RULE-015〜019 で機械検証 |
| DD-011 | TR の `result`・`log_ref` を YAML メタに昇格。body フィールドでは機械判定不可のため。RULE-020（result 必須）・RULE-021（FAIL 時 log_ref 必須）を追加。LOG ノード型は不要（単一 TR に内包で十分）。 |
| DD-012 | **kind 廃止**：辺は無名の依存辺。関係名は `(source 型, target 型)` から読み取る。冗長な kind フィールドを持たない |
| DD-013 | **status 廃止**：ドリフトは `ref_version` 比較が唯一の真実源。pending/done は ref_version 一致/不一致から導出され冗長。影響なしは ref_version を素直に更新する（旧 n/a 不要） |
| DD-014 | **see-also / replaces / extends / contradicts / decomposes 廃止**。参照＝依存（see-also 不要）・歴史情報は本文へ（replaces）・継承は無名依存辺（extends）・矛盾は FND（contradicts）・階層は ID パターン（decomposes） |
| DD-015 | **ref_version 全辺必須**（義務辺含む）。義務辺がドリフトしたら「決定が古い前提に立つ」シグナルになり見直しオペレーションを駆動する |
| DD-016 | **DD/Q/PEND 義務辺モデル**：`DD→X` 辺の存在＝未反映（RULE-001 ERROR）。反映完了で辺を削除し `X→DD` の依存辺を追加。逆向き辺は反映までの一時辺のみ |
| DD-017 | **依存方向統一**：全辺は依存先を指す。`O→P`（旧 produces 反転）・`P→E`（旧 triggers 反転）・`P→I`（consumes）・`O/E→ACTOR` |
| DD-018 | **D 型新設**（内部データフロー）：プロセス間で系外へ出ないデータ。`D→SPEC`・`D→P`・`P→D`。O→ACTOR ルールは D に適用しない |
| DD-019 | **ルール設定駆動化**：必須接続を `must_link_to`/`must_be_linked_from`（型ペア＋発火ステージ＋severity）で表現。旧 RULE-005/009〜013/015 を RULE-006 に吸収。旧 stage_scope.disable を activate_stage/rule_activation で代替 |
| DD-020 | **E→ACTOR 必須（ERROR）**：事象は刺激元アクタへの依存を持つ。系内の定期実行など「アクタなし事象」は事象ではなく FR で表現する |
