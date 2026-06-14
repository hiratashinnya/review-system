# 非機能要求・制約

> **型**: NFR ／ **必須上流**: SR（依存辺 ✅）
> NFR は検証結果から辺を受ける必要がある（`must_be_linked_from: NFR ← [FND,TC,VERIFY]`）。
> この接続は verification ステージで発火するため、現在（requirements）は沈黙（suppress 不要）。

---

## NFR-1: プレーンテキスト形式

<details><summary>⬡ NFR-1 · v0.3</summary>

```yaml
id: NFR-1
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-2
    ref_version: "0.1"
  - to: DD-1
    ref_version: "0.1"
  - to: DD-5
    ref_version: "0.1"
```
</details>

ノードファイルはプレーン Markdown＋YAML フロントマターで記述し、専用エディタ・専用フォーマットへの依存を持たない（GitHub でそのまま読める）。

---

## NFR-2: 標準ライブラリのみでパース可能

<details><summary>⬡ NFR-2 · v0.3</summary>

```yaml
id: NFR-2
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-2
    ref_version: "0.1"
  - to: DD-1
    ref_version: "0.1"
  - to: DD-5
    ref_version: "0.1"
```
</details>

検証ツールは Python 標準ライブラリのみで実装し、フロントマター・`<details>` ブロックのパースに外部依存を持たない（フロントマターも自前パーサ）。

---

## NFR-3: スキルは self-contained

<details><summary>⬡ NFR-3 · v0.2</summary>

```yaml
id: NFR-3
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-1
    ref_version: "0.1"
  - to: DD-5
    ref_version: "0.1"
```
</details>

各工程別スキルは著作に必要な情報をすべて内包し、スキル実行時に外部ファイル（07-authoring-guide 等）の読み込みを要求しない（コンテキスト汚染の回避）。

---

## NFR-4: ファイル単位バージョニング・1 ファイル 1 責務

<details><summary>⬡ NFR-4 · v0.2</summary>

```yaml
id: NFR-4
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-6
    ref_version: "0.1"
  - to: DD-5
    ref_version: "0.1"
```
</details>

バージョン管理の単位はファイル（frontmatter `version: x.y.z`）とし、1 ファイル＝1 責務（概念グループ）を保つことで、ファイル内 1 ノードの変化で全辺が pending になる粒度問題を許容範囲に抑える（DD-004・06§7）。

---

## NFR-5: 直接の親 1 段のみ・USDM 分割

<details><summary>⬡ NFR-5 · v0.2</summary>

```yaml
id: NFR-5
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-3
    ref_version: "0.1"
  - to: DD-5
    ref_version: "0.1"
```
</details>

各ノードは直接の親（隣接 1 段）のみへ辺を張り、全祖先への辺は持たない（推移到達はグラフ走査で計算）。FR（機能要求）と SPEC（テスタブル仕様）を USDM 分割し、分析層以降は SPEC を直接の親とする（DD-003/008・接続マトリクス D2/D3）。

---

## NFR-6: ライフサイクル状態は本文・メタに持たない

<details><summary>⬡ NFR-6 · v0.3</summary>

```yaml
id: NFR-6
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-2
    ref_version: "0.1"
  - to: DD-1
    ref_version: "0.1"
  - to: DD-5
    ref_version: "0.1"
```
</details>

DD/Q/PEND のライフサイクル状態（open/decided/closed 等）は本文の見出し・バッジに記載し、メタ属性には持たない。機械は型（DD/Q）で判定し、lifecycle のパースを要しない（DD-005・02§2）。
