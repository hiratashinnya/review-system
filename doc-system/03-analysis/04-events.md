---
version: "0.1.0"
---
# イベント

> **型**: E ／ **必須上流**: SPEC（refines ✅）
> E → P は **E 側** `kind: triggers`（P 側には書かない）。
> 本文は5要素（イベント名／スティミュラス／アクション／レスポンス／アフェクト）で記述。

---

## E-1: 文書提出

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

**イベント名**: 文書提出
**スティミュラス**: 利用者（ACTOR-1）が評価対象文書群（I-1）＋任意で型上書き（I-2）・スコープ（I-3）を提出する
**アクション**: P1（受付・正規化）→ P2（基準合成）→ P3（AI 評価）→ P4（検証・仕分け）→ P5（レポート生成）を順次実行する。基準パース失敗・LLM 障害・スコープ未解決は各段で fail-close する（E-14 参照）
**レスポンス**: O-1（レポートコンテナ）＋ O-2（指摘）・O-3（🤖 自動修正サマリ）・O-4（✋ diff）・O-5（💬 原案）・O-7（❓ 未分類）
**アフェクト**: レビュー負荷の削減と品質の均質化

---

## E-2: ✋ 承認/却下

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

**イベント名**: ✋ 承認/却下
**スティミュラス**: レビュアー（ACTOR-2）が ✋ 指摘に対して承認または却下の判断（I-6）を下す
**アクション**: P5.2 が承認案を文書に適用する。判断（承認/却下いずれも）を P6.1 に記録して育成素材とする。却下の場合は適用なし
**レスポンス**: O-3（適用結果＋サマリ）。育成記録は DS5 へ
**アフェクト**: 人間の判断が修正に反映され、自動化への信頼が積み上がる

---

## E-3: 💬 決定

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

**イベント名**: 💬 決定
**スティミュラス**: レビュアー（ACTOR-2）が 💬 指摘で提示された複数案から1つを選択・決定（I-6）する
**アクション**: P5.2 が選ばれた案を文書に適用する。決定を P6.1 に記録する
**レスポンス**: O-3（適用結果＋サマリ）
**アフェクト**: 「ゼロから考える」を「選ぶ」に変え、意思決定コストを下げる

---

## E-4: 🤖 「対象外」フラグ

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

**イベント名**: 🤖 「対象外」フラグ
**スティミュラス**: レビュアー（ACTOR-2）が 🤖 自動修正サマリを流し読みして、特定指摘に「対象外」フラグ（I-7）を立てる
**アクション**: P6.1 が違和感を finding 単位で記録し傾向を集計する。緩め方向の観点 FB 提案（O-12）の素材とする
**レスポンス**: DS5（フィードバック蓄積）への記録。即時の O-12 生成は E-10 で行う
**アフェクト**: レポートの流し読みがそのままチューニングデータになる

---

## E-5: revert 要求

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

**イベント名**: revert 要求
**スティミュラス**: 利用者（ACTOR-1）が自動適用済み修正の取り消し（I-14）を要求する（finding 単位または一括）
**アクション**: P5.4 が DS3（finding-commit ワークスペース）の対象コミットを revert する
**レスポンス**: O-6（revert 完了通知）
**アフェクト**: 安心して自動化レベルを上げられる

---

## E-9: LLM id 未付与/未知指摘

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

**イベント名**: LLM id 未付与/未知指摘
**スティミュラス**: P3 から返った findings の中に rule_id が付いていない、または既存 rule_id に一致しない指摘が含まれる（PF/LLM の生出力の限界・内部境界事象）
**アクション**: P4.1 が当該 finding を 3 区分の仕分け対象から除外し、❓ 未分類（O-7）へ退避・surfacing する。破棄しない
**レスポンス**: O-7（❓ 未分類・第4区分）
**アフェクト**: 取りこぼし防止。新ルール候補の可視化

---

## E-14: 異常系（基準パース失敗 / LLM 障害 / スコープ未解決）

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

**イベント名**: 異常系
**スティミュラス**: 各処理段で障害・不正状態が発生する（基準ファイルのパースエラー・LLM プラットフォーム障害/タイムアウト・doc_type に対応する基準ゼロ/スコープ未解決）
**アクション**: 発生段で処理を中断（fail-close）する。空文書のみ benign no-op（後続を起動しない）。上流失敗時は自動適用段（P5.2）を絶対に実行しない（SPEC-14）。per-unit graceful degrade は post-MVP（F16）
**レスポンス**: O-14（対象ファイル・失敗段・理由を含む明示エラー通知）。空文書の場合は O-14 なし
**アフェクト**: 誤適用・取りこぼしの防止。問題を明示して利用者・基準メンテナが対処できる
