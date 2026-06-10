---
version: "0.1.0"
---
# 非機能要求・制約

> **型**: NFR ／ **必須上流**: SR（refines ✅）
> RULE-011: FND からの `validates` 辺が必要（検証時に追加）。

---

## 自動化レベルはポリシーファイルで設定可能

<details><summary>⬡ NFR-1 · v0.1</summary>

```yaml
id: NFR-1
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-4
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

`determinism × severity → 適用モード` のマッピングを外部ポリシーファイル（I-5）で定義し、システム再デプロイなしに自動化範囲を変更できる。機械判定ロジックと運用ルールを混在させない。

---

## fail-close と明示エラー通知（O-14）

<details><summary>⬡ NFR-2 · v0.1</summary>

```yaml
id: NFR-2
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-1
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SR-2
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

基準パース失敗・LLM 障害・スコープ未解決では処理を中断（fail-close）し、原因・対象ファイルを O-14 として明示通知する。
空文書は benign no-op（O-14 不要）。上流失敗時は自動適用段（P5.2）を絶対に走らせない。

---

## Python 標準ライブラリのみ使用

<details><summary>⬡ NFR-3 · v0.1</summary>

```yaml
id: NFR-3
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

実装は Python・原則標準ライブラリのみ（サードパーティ依存なし）。フロントマターパーサも自前実装。

---

## LLM は外部 PF に委譲（アダプタ境界）

<details><summary>⬡ NFR-4 · v0.1</summary>

```yaml
id: NFR-4
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

LLM の判断・生成は外部 PF（Claude Code 等）に委譲し、システムはアダプタ経由で差し替え可能にする。
生 LLM 出力はすべてシステム内で検証・整形してから出力とする（素通し禁止）。
