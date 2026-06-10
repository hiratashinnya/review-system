---
version: "0.1.0"
---
# 外部アクタ

> **型**: ACTOR ／ **必須上流**: SR（refines ✅）

---

## 利用者（User）

<details><summary>⬡ ACTOR-1 · v0.1</summary>

```yaml
id: ACTOR-1
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

文書を提出してレビューレポートを受け取る書き手。revert 要求も行う。MVP ではレビュアーと同一人物でも可。

---

## レビュアー（Reviewer）

<details><summary>⬡ ACTOR-2 · v0.1</summary>

```yaml
id: ACTOR-2
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-2
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

指摘に対して承認・決定・「対象外」フラグを下す人間。MVP では ACTOR-1 と同一でも可（論理的には分離）。

---

## 基準メンテナ（Maintainer）

<details><summary>⬡ ACTOR-3 · v0.1</summary>

```yaml
id: ACTOR-3
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-3
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SR-4
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

評価基準ファイル（I-4）とポリシー（I-5）を管理・編集する。編集はシステム外（系外）で行う。観点 FB 提案（O-12）・合成時警告（O-9）を受け取る。

---

## PF・LLM プラットフォーム

<details><summary>⬡ ACTOR-4 · v0.1</summary>

```yaml
id: ACTOR-4
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

Claude Code 等の LLM プラットフォーム。判断・生成を担う外部エンティティ。システムはアダプタ経由で接続し、生出力を必ずシステム内検証にかける。
