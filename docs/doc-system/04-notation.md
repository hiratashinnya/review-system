---
version: "0.1.0"
---
# ノード＆エッジ記法

> `<details>` トグルを使った Markdown 埋め込み記法の確定仕様。
> ノード属性スキーマは [02](02-meta-schema.md)、接続要否は [03](03-connection-matrix.md)。

---

## 1. ファイル構造

各 Markdown ファイルは**1責務**（1ファイル＝1概念グループ）。複数ノードを同一ファイルに置く場合は `---` で区切る。

```markdown
---
version: "1.0.0"
---
# [ファイルタイトル]

> [ファイルの目的・概要（1–2行）]

## [ノード見出し]

<details><summary>⬡ PREFIX-N · vX.Y</summary>

```yaml
id: PREFIX-N
type: TYPE
...
```
</details>

[本文]

---

## [次のノード見出し]
...
```

---

## 2. ノードの埋め込み形式

### 完全形式

```markdown
## FR-001: [機能名]

<details><summary>⬡ FR-001 · v1.0</summary>

\`\`\`yaml
id: FR-001
type: FR
labels: []
scheduled: ""
edges:
  - to: SR-003
    ref_version: "1.0"
\`\`\`
</details>

[本文：機能要求の内容を1文で記述]
```

### summary 行の構文

```
⬡ <id> · v<x.y>
```

| 要素 | 内容 |
|---|---|
| `⬡` | ノードを示す固定記号（六角形アイコン） |
| `<id>` | ノード ID（例: FR-001, SPEC-003） |
| `v<x.y>` | 参照バージョン（ファイルの `version` の x.y）。z は省略 |

> summary 行のバージョンは**このノードが書かれた時点のファイル x.y**。  
> ドリフト検出の基準は辺の `ref_version` であり、summary は人の目印のみ。

---

## 3. YAML ブロックの書き方

### 基本属性（全ノード）

```yaml
id: FR-001          # 必須。PREFIX-N 形式。リネーム禁止。
type: FR            # 必須。§6 の型値から選択。
labels: []          # 任意。分類タグ（post-mvp, experimental 等）。
scheduled: ""       # 任意。後フェーズの場合、ルールが全サイレント。
```

### SPEC・TD 専用

```yaml
condition: normal   # normal | boundary | empty | failure | error
```

### TR 専用

```yaml
result: PASS        # PASS | FAIL
log_ref: ""         # ログのパス/URL（FAIL 時は必須）
```

### suppress（任意）

```yaml
suppress: [RULE-018]   # 理由を inline comment で必ず記載
```

### edges の書き方

```yaml
edges:
  # 基本形（1辺1 to・kind/status なし）
  - to: SR-003
    ref_version: "1.0"

  # 複数依存は辺を分割（リスト記法は禁止）
  - to: SPEC-001
    ref_version: "1.2"
  - to: SPEC-002
    ref_version: "1.2"

  # note 付き
  - to: NFR-001
    ref_version: "1.0"
    note: "パフォーマンス制約のみ。セキュリティは NFR-002 で別途"
```

- **`kind` は書かない**（辺は無名依存辺。関係名は型ペアから読む・02§5）。
- **`status` は書かない**（ドリフトは ref_version 比較が真実源・02§7）。
- **`to` はスカラーのみ**。複数先は辺を分割する。
- **`ref_version` は全辺必須**（DD/Q/PEND の義務辺含む）。

### ドリフトの考え方（status 廃止）

| 状態 | 表現 |
|---|---|
| 反映済み | `ref_version` が参照先の現在 x.y と一致 |
| 未反映（ドリフト） | `ref_version` が古い → RULE-004 ERROR。見直して ref_version を更新する |
| DD/Q/PEND の未反映 | 義務辺 `DD→X` が存在する（反映後に削除し `X→DD` を追加） |

---

## 4. 本文の位置

本文（説明・前提条件・期待動作等）は `</details>` の**後ろ**に書く。

```markdown
<details><summary>⬡ SPEC-001 · v1.0</summary>

```yaml
...
```
</details>

**前提条件**: 認証済みユーザーがいる
**入力/トリガ**: 有効な PR URL を入力
**期待動作**: レビュー結果が stdout に出力される
```

> YAML ブロック内に本文を混在させない。YAML は機械読み取り対象・本文は人向け。

---

## 5. 複数ノードの配置

同一ファイルに複数ノードを置く場合、見出し（`##`）とセパレータ（`---`）で区切る。

```markdown
---
version: "1.0.0"
---
# 機能要求

## FR-001: レビュー実行

<details><summary>⬡ FR-001 · v1.0</summary>

```yaml
...
```
</details>

[FR-001 の本文]

---

## FR-002: 結果出力

<details><summary>⬡ FR-002 · v1.0</summary>

```yaml
...
```
</details>

[FR-002 の本文]
```

---

## 6. 横断スパインの記法（DD / Q / PEND）

横断スパインのノードはライフサイクルを本文に持つ。メタ属性に状態は持たない（DD-005）。

```markdown
## DD-011: TR の result/log_ref をメタに昇格

<details><summary>⬡ DD-011 · v0.1</summary>

```yaml
id: DD-011
type: DD
edges:
  - to: FR-003
    ref_version: "1.0"
  - to: TC-001
    ref_version: "1.0"
```
</details>

**status: decided**

> DD の out 辺は義務辺。反映が完了したら辺を削除し、対象側に `FR-003 → DD-011` の依存辺を張る。

**論点**: ログを body フィールドにするか YAML メタにするか  
**選択肢**: A. YAML メタ昇格（機械チェック可） / B. body のまま  
**決定**: A。body では result/log_ref が機械判定不可のため。  
**影響範囲**: TR テンプレート・RULE-020/021 追加・test-strategy の成績書形式
```

未決（Q）の場合は `**status: open**` で、決定後に `decided` へ更新する。

---

## 7. 略記・省略ルール

| 場面 | 許可 | 禁止 |
|---|---|---|
| labels が空 | `labels: []` または `labels:` どちらも可 | 省略（キーごと消す）は不可 |
| scheduled が未設定 | `scheduled: ""` または省略可 | — |
| condition（SPEC/TD） | — | 省略すると RULE-016 **ERROR** |
| result（TR） | — | 省略すると RULE-020 **ERROR** |
| ref_version | — | **全辺必須**（省略不可・RULE-004 の基準） |
| note | 任意（省略可） | — |
| kind / status | — | **フィールドごと禁止**（廃止） |
| to のリスト | — | **禁止**（1辺1 to に分割） |

---

## 8. 検索・解析のための規約

検証ツールがノードを発見するためのパース規約。

```
# ノード発見
<details><summary>⬡ <ID> · ... の行の次の yaml ブロックをパース

# ファイルバージョン発見
frontmatter の version フィールド（x.y.z）

# エッジ発見
edges: リスト内の to/ref_version/note を読み取る（kind/status は存在しない）
```

> 検証ツールはこの記法に依存して YAML を抽出する。  
> `<details>` の構文を崩すとパースが壊れるため、記法を変える場合はツールとの同時更新が必要。
