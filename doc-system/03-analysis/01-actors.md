---
version: "0.2.0"
---
# 外部アクタ

> **型**: ACTOR ／ **必須上流**: SR（refines ✅）

---

## ACTOR-1: 仕様著者

<details><summary>⬡ ACTOR-1 · v0.1</summary>

```yaml
id: ACTOR-1
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-1
    ref_version: "0.2"
```
</details>

doc-system の規約に従いノードを作成・更新する人。スキルを呼び出してノードを書き、ID採番・辺設定・RULE確認を行う。

---

## ACTOR-2: レビュアー

<details><summary>⬡ ACTOR-2 · v0.1</summary>

```yaml
id: ACTOR-2
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-2
    ref_version: "0.2"
```
</details>

仕様の網羅性・整合性を確認する人。spec-inspector の出力を受け取り、指摘（G#）を評価・承認する。

---

## ACTOR-3: spec-inspector

<details><summary>⬡ ACTOR-3 · v0.1</summary>

```yaml
id: ACTOR-3
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-4
    ref_version: "0.2"
```
</details>

ノードセットをパースして RULE 違反とカバレッジ穴を検出する自動点検エージェント。G# 番号付きレポートを生成する。
