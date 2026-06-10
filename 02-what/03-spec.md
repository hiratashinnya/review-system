---
version: "0.1.0"
---
# 機能仕様（テスタブル粒度）

> **型**: SPEC ／ **必須上流**: FR（refines ✅）
> RULE-015: TD からの `verifies` 辺が必要。`scheduled: "verification"` で検証フェーズまでサイレント。
> RULE-016: `condition` 属性必須（normal / boundary / failure / error）。
> 1 ノード = 1 condition。

---

<!-- ============================================================ -->
<!-- FR-1: 評価対象文書の受付・正規化 -->
<!-- ============================================================ -->

## SPEC-1: 有効な文書ファイルを受け付けて正規化できる

<details><summary>⬡ SPEC-1 · v0.1</summary>

```yaml
id: SPEC-1
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 評価対象ファイル群が1件以上ある。文書タイプが I-2（上書き）または I-15（推定）で確定している。
**入力/トリガ**: 利用者が評価対象群（I-1）を提出する。
**期待動作**: P1 が文書タイプ・スコープを確定し、後段に渡せる正規化済み入力セットを生成する。

---

## SPEC-2: 空文書（対象ゼロ）は no-op で終了する

<details><summary>⬡ SPEC-2 · v0.1</summary>

```yaml
id: SPEC-2
type: SPEC
condition: failure
labels: []
scheduled: "verification"
edges:
  - to: FR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 提出されたファイル群に評価対象が0件である。
**入力/トリガ**: 評価対象ゼロの提出。
**期待動作**: fail-open（benign no-op）。O-14 を出さず、後段処理を開始しない。

---

## SPEC-3: 基準パース失敗時は fail-close + O-14 を出す

<details><summary>⬡ SPEC-3 · v0.1</summary>

```yaml
id: SPEC-3
type: SPEC
condition: error
labels: []
scheduled: "verification"
edges:
  - to: FR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 受付段（P1/P2）で基準ファイルのパースに失敗する状態。
**入力/トリガ**: 不正な基準ファイルが混在する提出。
**期待動作**: 全体を fail-close で停止。O-14 に「対象ファイル・行・失敗理由」を含めて通知。後段は一切動かさない。

---

<!-- ============================================================ -->
<!-- FR-2: 評価基準ファイルの合成 -->
<!-- ============================================================ -->

## SPEC-4: doc_type に対応する観点パックを合成できる

<details><summary>⬡ SPEC-4 · v0.1</summary>

```yaml
id: SPEC-4
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-2
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: doc_type が確定しており、対応する観点ファイルが1件以上ある（org スコープ）。
**入力/トリガ**: 正規化済み文書入力と doc_type。
**期待動作**: 対応する I-4 観点ファイルを継承・union 合成し、評価に使う観点パックを生成する。

---

## SPEC-5: doc_type に観点ファイルがない場合は fail-close + O-14

<details><summary>⬡ SPEC-5 · v0.1</summary>

```yaml
id: SPEC-5
type: SPEC
condition: failure
labels: []
scheduled: "verification"
edges:
  - to: FR-2
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 確定した doc_type に対応する観点ファイルが存在しない（またはスコープ未解決）。
**入力/トリガ**: 未対応 doc_type の提出。
**期待動作**: fail-close。O-14 に「doc_type=X の基準がない」を通知。空既定にフォールバックしない。

---

<!-- ============================================================ -->
<!-- FR-3: AI による指摘の生成 -->
<!-- ============================================================ -->

## SPEC-6: 観点に沿った指摘（findings）を生成できる

<details><summary>⬡ SPEC-6 · v0.1</summary>

```yaml
id: SPEC-6
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 観点パックと評価対象が正常に用意されている。PF（LLM）が稼働中。
**入力/トリガ**: 観点パック＋評価対象をプロンプト雛形に組み込んだ PF 呼び出し。
**期待動作**: PF から findings（生 LLM 出力）が返り、後段の検証・仕分けに渡せる。

---

## SPEC-7: LLM 障害時は bounded retry 後 fail-close + O-14

<details><summary>⬡ SPEC-7 · v0.1</summary>

```yaml
id: SPEC-7
type: SPEC
condition: error
labels: []
scheduled: "verification"
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: PF（LLM プラットフォーム）が到達不可またはタイムアウト。
**入力/トリガ**: PF 呼び出しの失敗。
**期待動作**: bounded retry（回数設定内）後も失敗 → fail-close。O-14 に「障害段・リトライ結果」を通知。自動適用（P5.2）は走らせない。

---

<!-- ============================================================ -->
<!-- FR-4: 指摘の検証・仕分け -->
<!-- ============================================================ -->

## SPEC-8: findings を rule_id 検証後に3区分で仕分けできる

<details><summary>⬡ SPEC-8 · v0.1</summary>

```yaml
id: SPEC-8
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-4
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: PF からの findings が正常に取得されている。ポリシーファイル（I-5）が読み込まれている。
**入力/トリガ**: 生 findings ＋ ポリシー（I-5）の組み合わせ。
**期待動作**: rule_id の実在確認・ポリシー参照後、各 finding を 🤖/✋/💬 に分類する。

---

## SPEC-9: rule_id 未付与の指摘は❓未分類に退避する

<details><summary>⬡ SPEC-9 · v0.1</summary>

```yaml
id: SPEC-9
type: SPEC
condition: boundary
labels: []
scheduled: "verification"
edges:
  - to: FR-4
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: PF が rule_id を付与できなかった（未知の指摘・自己申告）finding が含まれる。
**入力/トリガ**: id なし / 既存 rule_id に一致しない finding。
**期待動作**: 3区分に仕分けせず ❓ 未分類（O-7）へ退避・surfacing する。破棄しない。

---

<!-- ============================================================ -->
<!-- FR-5: 仕分け済みレポートの出力 -->
<!-- ============================================================ -->

## SPEC-10: 仕分け済み指摘を3区分+未分類のレポートとして出力できる

<details><summary>⬡ SPEC-10 · v0.1</summary>

```yaml
id: SPEC-10
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-5
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 仕分け済み findings（🤖/✋/💬/❓）が揃っている。
**入力/トリガ**: 仕分け完了。
**期待動作**: O-1（コンテナ）＋ O-2（指摘）・O-3（自動修正サマリ）・O-4（✋diff）・O-5（💬原案）・O-7（❓未分類）を生成・出力する。

---

<!-- ============================================================ -->
<!-- FR-6: 承認・決定済み修正の人手適用 -->
<!-- ============================================================ -->

## SPEC-11: 承認済み修正を文書に適用できる

<details><summary>⬡ SPEC-11 · v0.1</summary>

```yaml
id: SPEC-11
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-6
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: レビュアーが ✋/💬 指摘に対して承認・決定（I-6）を下している。
**入力/トリガ**: 指摘への判断（I-6）受信。
**期待動作**: 指定された修正を文書に適用し、適用結果（O-3）を記録する。

---

<!-- ============================================================ -->
<!-- FR-7: 自動修正の適用と revert -->
<!-- ============================================================ -->

## SPEC-12: 決定的ツール範囲の修正を自動適用できる

<details><summary>⬡ SPEC-12 · v0.1</summary>

```yaml
id: SPEC-12
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 検証・仕分けがクリーン完了している。🤖 指摘が1件以上ある。
**入力/トリガ**: 🤖 仕分け結果（finding 単位）。
**期待動作**: 決定的ツール範囲の修正を finding 単位でコミット（DS3 内部 git）し、適用サマリ（O-3）を生成する。

---

## SPEC-13: 自動適用済み修正を finding 単位で revert できる

<details><summary>⬡ SPEC-13 · v0.1</summary>

```yaml
id: SPEC-13
type: SPEC
condition: normal
labels: []
scheduled: "verification"
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 自動適用済みのコミットが DS3 に存在する。
**入力/トリガ**: revert 要求（finding 単位 / 一括）。
**期待動作**: 指定 finding のコミットを revert し、revert 結果（O-6）を返す。

---

## SPEC-14: 上流失敗時は自動適用を走らせない

<details><summary>⬡ SPEC-14 · v0.1</summary>

```yaml
id: SPEC-14
type: SPEC
condition: error
labels: []
scheduled: "verification"
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 上流（④評価 P3 / ⑤検証 P4）が失敗またはクリーン未完了。
**入力/トリガ**: 上流段の fail-close または異常終了。
**期待動作**: P5.2（自動適用段）を一切実行しない。DS3 に半端なコミットを残さない。O-14 が上流から通知済み。
