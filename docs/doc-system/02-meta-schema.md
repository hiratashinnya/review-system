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
| **x（メジャー）** | 構造破壊（要素の追加/削除/型変更） | `ref_version` の `x.y` 不一致 → `status: pending` |
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
scenario:  string     # SPEC/TD のみ推奨。シナリオ分類（§2a 参照）。
                      # 省略時は RULE-016 で WARNING。
```

> **ライフサイクル状態（DD/Q/PEND）はメタ属性に持たない**。本文の見出しや
> バッジ（`**status: decided**`）に記載する。理由：ライフサイクルは人が読む情報であり、
> 機械が状態を読む必要があれば本文パースで取得できる。

> **バージョンはノードに持たない**。ファイル単位で管理（§1）。

---

## 2a. scenario 属性（SPEC・TD 専用）

> **目的**：シナリオ種別を機械可読にして、FR ごとの仕様カバレッジを次元別に検証する。
> **適用型**：`SPEC`・`TD`（それ以外に付与しても無視）

### 語彙（config.yaml の `scenario_vocab` で拡張可能）

| 値 | 意味 | 典型例 |
|---|---|---|
| `normal` | 正常系（成立）：前提が満たされ期待通りに動く | 正常な入力 → 200 OK |
| `failure` | 失敗系（不成立）：業務ルール違反・バリデーション失敗 | 必須項目欠落 → 400 |
| `error` | 異常系：インフラ障害・タイムアウト・予期しない例外 | DB 接続断 → 503 |

> 語彙は固定ではなく `config.yaml` に `scenario_vocab` を追加することで拡張できる。
> デフォルト語彙はこの3値。

### TD の scenario は SPEC から導出する

`TD` の `scenario` は `verifies` 辺で指す `SPEC` の `scenario` と一致させることを推奨。
一致しない場合 RULE-019 で WARNING を出す（設計ミスの早期発見）。

### カバレッジ検証の次元

```
FR-001
  ├─ SPEC-001  scenario: normal   ← RULE-015 ✅ TD あり
  ├─ SPEC-002  scenario: failure  ← RULE-015 ✅ TD あり
  └─ SPEC-003  scenario: error    ← RULE-015 ⚠️ TD なし  ← RULE-015 発火
```

RULE-017 は FR → SPEC 方向で「正常系仕様が定義されているか」を検証する。

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
- 親ノードは子ノードへ `decomposes` 辺を持つ（子が追加されたときに親辺を追加）。
- doc-system 自身の意思決定も同じ id 空間（`DD-001`, `Q-001` など）。

---

## 4. エッジ属性スキーマ

```yaml
edges:
  - to:          string | [string]  # 必須：参照先ノード id（単数または複数）
    kind:        string             # 必須：関係種別（§5）
    status:      string             # 必須：伝播ステータス（§7）
    ref_version: string             # 推奨：参照先ファイルの x.y（ドリフト検出に使用）
    note:        string             # 任意：補足・理由
```

### `to` の複数指定

同一 kind・同一 status・同一 ref_version で複数ノードへ辺を張る場合は配列で書ける。

```yaml
edges:
  # 単一
  - to: FR-009
    kind: refines
    status: done
    ref_version: "1.2"

  # 複数（同じ関係・同じステータス）
  - to: [SR-003, VAL-001]
    kind: refines
    status: done
    ref_version: "2.0"
```

---

## 5. エッジ関係種別（kind）

### 階層・精緻化

| kind | 意味 | 典型例 |
|---|---|---|
| `refines` | 上位概念を詳細化する（層間の主辺） | `FR-001 → SR-001`, `DM-001 → TERM-001` |
| `decomposes` | 親要素が子要素に分割された | `I-1 → I-1-1`, `I-1 → I-1-2` |

### 実現

| kind | 意味 | 典型例 |
|---|---|---|
| `realizes` | コード/設計が仕様を実現する | `SRC → DM-001`, `SRC → PORT-001` |
| `allocates-to` | 要求をコンポーネント/モジュールに割当 | `FR-003 → MOD-002` |
| `instantiates` | コンフィグ/インスタンスが設計を具体化 | `CFG-001 → SCM-001` |

### データフロー

| kind | 意味 | 典型例 |
|---|---|---|
| `triggers` | イベント/入力がプロセスを起動する | `E-001 → P-001` |
| `produces` | プロセスが出力を生成する | `P-002 → O-001` |
| `consumes` | プロセスが入力を消費する | `P-001 → I-001` ※方向注意：`I-001` が起点でも可 |

> `P` と `I`/`O` の接続は `consumes`/`produces` を使う。`I-001` が `P-001` を
> `consumes` するか、`P-001` が `I-001` を `consumes` するかは実装時に統一する（03 §7 参照）。

### 検証

| kind | 意味 | 典型例 |
|---|---|---|
| `verifies` | テスト/検証が要求・コードを検証する | `TC-001 → FR-003`, `TC-001 → SRC` |
| `validates` | 検証結果が NFR/制約を証明する | `FND-001 → NFR-002` |
| `found-in` | 指摘が対象要素の中に発見された | `FND-001 → DM-005` |

### 制約

| kind | 意味 | 典型例 |
|---|---|---|
| `constrains` | NFR/制約が設計・実装を制約する | `NFR-001 → MOD-003` |

### 意思決定

| kind | 意味 | 典型例 |
|---|---|---|
| `affects` | 決定/指摘が要素に影響する | `DD-015 → DM-001`, `Q-003 → FR-007` |
| `replaces` | 新要素が旧要素を置換/supersede する | `FR-010 → FR-007` |

### 参照

| kind | 意味 | 伝播 |
|---|---|---|
| `see-also` | 参考情報（関連するが依存ではない） | **なし** |
| `extends` | 継承・拡張（スキーマ継承・設計継承） | あり |
| `uses` | コンポーネント/段が別の要素を利用する（ORC が PROMPT を使う等） | あり |

### 実行証跡

| kind | 意味 | 典型例 |
|---|---|---|
| `produced-by` | テスト結果がテストコードの実行から生成された | `TR-001 → TC-001` |

### 矛盾

| kind | 意味 |
|---|---|
| `contradicts` | 2要素間の矛盾を明示（spec-inspector が起票） |

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
| `I` | `I-` | 分析 | 入力 |
| `O` | `O-` | 分析 | 出力 |
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

## 7. エッジ伝播ステータス（status）

| 値 | 意味 |
|---|---|
| `pending` | 上流の変化がこの辺の先にまだ反映されていない |
| `done` | 反映済み |
| `n/a` | トレース上辺は存在するが伝播反映は不要（影響なしと確認済み） |

### ドリフト検出ルール

```
# バージョンドリフト（RULE-003）
edge.ref_version の x.y ≠ 参照先ファイルの現在 version の x.y
  → status を pending に更新（検証ツールが検出・報告）

# 意思決定ドリフト（RULE-001）
DD ノードの affects 辺に status: pending が残っている
  → 反映漏れ確定（ドリフト検出の核心）
  ※ DD はノードの型で判定する。lifecycle状態のパース不要。
```

### ステータス遷移

```
[新規辺作成]           → pending
[反映完了]             → done
[影響なしと確認]        → n/a
[上流ファイル x.y 上昇] → refines/realizes/verifies 辺を done → pending へリセット
```

---

## 8. ルール抑制仕様

> 設定ファイル：`docs/doc-system/config.yaml`

### 抑制の2軸

| 軸 | 設定 | 条件 | 効果 |
|---|---|---|---|
| **scheduled 抑制** | ノード属性 `scheduled` | `scheduled` のフェーズが `current_phase` より後 | **完全サイレント**（ルール非発火） |
| **ステージ抑制** | `config.yaml` の `stage_scope` | ノードの型が `current_stage` の `warn` リストに該当 | **ERROR → WARNING に降格**（発火するが警告のみ） |

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

### ステージ抑制の判定

```
stage_scope[current_stage].warn にノードの type が含まれる
  → ERROR ルールを WARNING に降格して発火

stage_scope[current_stage].full にノードの type が含まれる
  → 元の深刻度のまま発火
```

### 抑制の例外

**RULE-007（存在しない ID への参照）は抑制対象外**。  
scheduled/stage に関わらず常に ERROR。存在しない ID を参照している時点でグラフが壊れており、フェーズを待つ意味がない。

### config.yaml の構造

```yaml
# docs/doc-system/config.yaml

current_phase: "sprint-1"
current_stage: "requirements"

phases:
  - sprint-1
  - sprint-2
  - sprint-3
  - post-mvp

stage_scope:
  requirements:
    full: [VAL, SR, FR, NFR]
    warn: [TERM, ACTOR, I, O, P, E, ORC, DS, MOD, DM, PORT, PRS, SCM, CFG, PROMPT, SRC, TC, VERIFY, FND, DD, Q, PEND]
  analysis:
    full: [VAL, SR, FR, NFR, TERM, ACTOR, I, O, P, E]
    warn: [ORC, DS, MOD, DM, PORT, PRS, SCM, CFG, PROMPT, SRC, TC, VERIFY, FND]
  design:
    full: [VAL, SR, FR, NFR, TERM, ACTOR, I, O, P, E, ORC, DS, MOD, DM, PORT, PRS, SCM, CFG, PROMPT]
    warn: [SRC, TC, VERIFY, FND]
  implementation:
    full: [VAL, SR, FR, NFR, TERM, ACTOR, I, O, P, E, ORC, DS, MOD, DM, PORT, PRS, SCM, CFG, PROMPT, SRC, TC]
    warn: [VERIFY, FND]
  verification:
    full: [VAL, SR, FR, NFR, TERM, ACTOR, I, O, P, E, ORC, DS, MOD, DM, PORT, PRS, SCM, CFG, PROMPT, SRC, TC, VERIFY, FND]
    warn: []

always_error:
  - RULE-007
```

---

## 9. ドリフト検出・検証ルール

> 検証ツールが走査するルールの完全定義。
> 深刻度：**ERROR**（必ず解消）／**WARNING**（要確認・合理的な理由があれば n/a 許容）／**INFO**（記録のみ）

### グループ A：意思決定ドリフト（C1）

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-001** | `DD` ノードの `affects` 辺 | `status: pending` が残っている | **ERROR** | `DD-015 → DM-001 が未反映（affects pending）` |
| **RULE-002** | `Q` ノードの `affects` 辺 | `status: pending` が残っている | **WARNING** | `Q-003 → FR-007 が未追跡（未決論点の影響候補）` |

> **DD は型で判定**：lifecycle状態（decided/open）を本文からパースせず、
> ノード型が `DD` であれば `affects` の `pending` は無条件 ERROR。
> `Q` は未決なので WARNING 止まり。反映完了時は `done`、影響なしと確定したら `n/a` に更新する。

---

### グループ B：バージョンドリフト

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-003** | `ref_version` を持つ辺 | `ref_version` の x.y ≠ 参照先ファイルの現在 version の x.y | **WARNING** | `DM-001 → TERM-003 の ref_version 1.2 が古い（現: 1.4.0）` |
| **RULE-004** | `refines`/`realizes`/`verifies` 辺 | RULE-003 かつ kind が上記 3 種のいずれか | **ERROR** | 同上（主要辺は ERROR に昇格） |

---

### グループ C：構造的な接続不足

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-005** | `VAL`/`ACTOR`/`I`/`O`/`E` ノード | `see-also` を除く辺が 0 本 | **ERROR** | `I-3 が孤立している（辺が必要）` |
| **RULE-006** | 03 マトリクスで ✅ の辺 | 必須の上流リンクが存在しない | **ERROR** | `DM-005 に TERM への refines 辺がない` |
| **RULE-007** | 辺の `to` フィールド | 参照先 ID が存在しない | **ERROR** | `辺 FR-009 → SR-999 の参照先 SR-999 が未定義` |
| **RULE-008** | 階層 ID（例: `I-1-1`） | 親ノード（`I-1`）に `decomposes` 辺がない | **WARNING** | `I-1-1 の親 I-1 に decomposes 辺がない` |

---

### グループ D：検証・指摘の完結性

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-009** | `FND` ノード | `found-in` 辺も `validates` 辺も 0 本 | **ERROR** | `FND-007 に辺がない（found-in または validates が必要）` |
| **RULE-010** | `FND` ノード | `found-in` 辺が 0 本（`validates` のみ存在） | **WARNING** | `FND-007 に found-in がない（何の中に見つかったか不明）` |
| **RULE-011** | `NFR` ノード | 入力方向の `validates` 辺が 0 本 | **WARNING** | `NFR-002 に validates 辺がない（検証証跡が必要）` |
| **RULE-012** | `TC` ノード | `verifies` 辺が 0 本 | **ERROR** | `TC-012 に verifies 辺がない` |
| **RULE-013** | `VERIFY` ノード | `verifies` 辺が 0 本 | **ERROR** | `VERIFY-003 に verifies 辺がない` |

---

### グループ E：`see-also` の伝播禁止

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-014** | `see-also` 辺 | `status: pending` または `done` が付いている | **WARNING** | `see-also 辺に伝播ステータスは不要（n/a に統一）` |

> `see-also` は情報的参照のみ。伝播ステータスは `n/a` 固定とし、ドリフト検出対象外。

---

### グループ F：仕様カバレッジ

| RULE# | 対象 | 条件 | 深刻度 | メッセージ例 |
|---|---|---|---|---|
| **RULE-015** | `SPEC` ノード | 入力方向の `verifies` 辺（from `TD`）が 0 本 | **WARNING** | `SPEC-003 にテスト設計（TD）が紐づいていない（カバレッジ未確保）` |
| **RULE-016** | `SPEC`・`TD` ノード | `scenario` 属性がない | **WARNING** | `SPEC-002 に scenario 属性がない（カバレッジ次元が不明）` |
| **RULE-017** | `FR` ノード | refines している `SPEC` 群に `scenario: normal` がひとつもない | **WARNING** | `FR-005 に正常系仕様（scenario: normal の SPEC）がない` |
| **RULE-018** | `FR` ノード | refines している `SPEC` 群に `scenario: failure` も `scenario: error` もない | **INFO** | `FR-005 に失敗系・異常系の仕様がない（意図的であれば labels: [no-error-path] で抑制可）` |
| **RULE-019** | `TD` ノード | `scenario` が `verifies` 先 `SPEC` の `scenario` と不一致 | **WARNING** | `TD-003 (scenario: normal) が SPEC-002 (scenario: failure) を verifies している` |

> RULE-015：テスト設計の存在を保証する。
> RULE-016：シナリオ種別を明示させる（分類なしでは次元別カバレッジ計算不可）。
> RULE-017：正常系が定義されていない FR を検出。全 FR に正常系仕様は必須。
> RULE-018：INFO のみ（意図的に error path がない FR も存在するため）。`labels: [no-error-path]` で抑制。
> RULE-019：TD の scenario と検証対象 SPEC の scenario が食い違うと設計ミスの兆候。

---

### ルール一覧サマリ

| RULE# | グループ | 深刻度 | 一言説明 |
|---|---|---|---|
| RULE-001 | A | ERROR | DD の affects pending = 反映漏れ |
| RULE-002 | A | WARNING | Q の affects pending = 未追跡 |
| RULE-003 | B | WARNING | ref_version 不一致 |
| RULE-004 | B | ERROR | 主要辺（refines/realizes/verifies）の ref_version 不一致 |
| RULE-005 | C | ERROR | VAL/ACTOR/I/O/E の孤立 |
| RULE-006 | C | ERROR | 必須上流リンクの欠如 |
| RULE-007 | C | ERROR | 存在しない ID への参照 |
| RULE-008 | C | WARNING | 階層 ID の親 decomposes 辺なし |
| RULE-009 | D | ERROR | FND に辺が 0 本 |
| RULE-010 | D | WARNING | FND に found-in なし |
| RULE-011 | D | WARNING | NFR に validates なし |
| RULE-012 | D | ERROR | TC に verifies なし |
| RULE-013 | D | ERROR | VERIFY に verifies なし |
| RULE-014 | E | WARNING | see-also に伝播ステータス付与 |
| RULE-015 | F | WARNING | SPEC に TD からの verifies なし（カバレッジ未確保） |
| RULE-016 | F | WARNING | SPEC/TD に scenario 属性なし |
| RULE-017 | F | WARNING | FR に scenario: normal の SPEC がない |
| RULE-018 | F | INFO | FR に failure/error シナリオの SPEC がない |
| RULE-019 | F | WARNING | TD の scenario が verifies 先 SPEC の scenario と不一致 |

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
| DD-010 | scenario はメタ属性（sub-ID 案を退ける）。ID に意味を持たせない DD-002 の原則を優先。語彙固定（normal/failure/error）＋config.yaml 拡張可。FR×scenario×TD の3次元カバレッジを RULE-015〜019 で機械検証 |
