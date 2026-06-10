---
version: "0.1.0"
---
# イベント

> **型**: E ／ **必須上流**: SPEC（refines ✅）
> E → P は **E 側** `kind: triggers`（P 側には書かない）。

---

## E1: 文書を提出する

<details><summary>⬡ E-1 · v0.1</summary>

```yaml
id: E-1
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-1
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**トリガ**: 利用者（ACTOR-1）が評価対象文書群（I-1）を提出する
**反応**: P1（受付・正規化）→ P2（基準合成）→ P3（AI 評価）→ P4（検証・仕分け）→ P5（レポート出力）が連続して実行される。O-1〜O-7 が生成される。

---

## E2: ✋ 提案を承認/却下する

<details><summary>⬡ E-2 · v0.1</summary>

```yaml
id: E-2
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-11
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-5
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**トリガ**: レビュアー（ACTOR-2）が ✋ 指摘に承認または却下（I-6）を下す
**反応**: 承認 → P5.2 で修正を適用（O-3）。判断は P6.1 に記録（育成素材）。

---

## E3: 💬 原案から決定する

<details><summary>⬡ E-3 · v0.1</summary>

```yaml
id: E-3
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-11
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-5
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**トリガ**: レビュアー（ACTOR-2）が 💬 指摘で提示された複数案から1つを選択・決定（I-6）する
**反応**: 選ばれた案を P5.2 で適用（O-3）。決定を P6.1 に記録。

---

## E4: 🤖 自動修正に「対象外」フラグを立てる

<details><summary>⬡ E-4 · v0.1</summary>

```yaml
id: E-4
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-10
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-6
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**トリガ**: レビュアー（ACTOR-2）がレポートを流し読みして 🤖 サマリに「対象外」フラグ（I-7）を立てる
**反応**: P6.1 が違和感を記録・傾向集計（O-12 の素材）。

---

## E5: 自動修正を revert する

<details><summary>⬡ E-5 · v0.1</summary>

```yaml
id: E-5
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-13
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-5
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**トリガ**: 利用者（ACTOR-1）が自動適用済み修正の取り消しを要求（I-14）する（finding 単位 / 一括）
**反応**: P5.4 が DS3 の finding コミットを revert し、O-6 を返す。

---

## E9: LLM が rule_id 未付与/未知の指摘を出す

<details><summary>⬡ E-9 · v0.1</summary>

```yaml
id: E-9
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-9
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-4
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**トリガ**: P3 から返った findings の中に rule_id が付いていない / 既存 ID に一致しないものが含まれる（内部境界事象）
**反応**: P4.1 が ❓ 未分類（O-7）へ退避・surfacing。破棄しない。

---

## E14: 異常系（基準パース失敗 / LLM 障害 / スコープ未解決）

<details><summary>⬡ E-14 · v0.1</summary>

```yaml
id: E-14
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-5
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-7
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-14
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**トリガ**: 各段で発生する障害・不正状態（基準パース失敗・LLM 障害・スコープ未解決）
**反応**: 原則 fail-close → O-14（対象ファイル・失敗段・理由）を通知。空文書のみ benign no-op（O-14 なし）。自動適用（P5.2）は一切走らせない。per-unit graceful degrade は post-MVP（F16）。
