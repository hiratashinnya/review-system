---
version: "0.1.0"
---
# 非機能要求・制約

> **型**: NFR ／ **必須上流**: SR（refines ✅）

---

## NFR-1: プレーンテキスト形式

<details><summary>⬡ NFR-1 · v0.1</summary>

```yaml
id: NFR-1
type: NFR
labels: []
scheduled: ""
suppress: [RULE-011]  # 検証フェーズ未到達: VERIFY/FND ノード未作成（scheduled: verification で代替）
edges:
  - to: SR-4
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

ノードファイルはプレーンMarkdown＋YAMLフロントマターで記述し、専用ツールへの依存を持たない。

---

## NFR-2: 標準ライブラリのみでパース可能

<details><summary>⬡ NFR-2 · v0.1</summary>

```yaml
id: NFR-2
type: NFR
labels: []
scheduled: ""
suppress: [RULE-011]  # 検証フェーズ未到達: VERIFY/FND ノード未作成（scheduled: verification で代替）
edges:
  - to: SR-4
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

フロントマターの形式はPython標準ライブラリのみで解析可能な範囲に限定し、外部依存ゼロを維持する。

---

## NFR-3: スキルはself-contained

<details><summary>⬡ NFR-3 · v0.1</summary>

```yaml
id: NFR-3
type: NFR
labels: []
scheduled: ""
suppress: [RULE-011]  # 検証フェーズ未到達: VERIFY/FND ノード未作成（scheduled: verification で代替）
edges:
  - to: SR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

各工程別スキルは著作に必要な情報をすべて内包し、スキル実行時に外部ファイルの読み込みを要求しない。
