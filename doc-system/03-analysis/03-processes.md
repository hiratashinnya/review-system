---
version: "0.4.0"
---
# 論理プロセス

> **型**: P ／ **必須上流**: SPEC（依存辺 ✅）
> 依存方向（DD-017）：P→I/P→D（消費）・P→E（トリガ事象に依存）。
> 生成（O→P・D→P）は O/D 側に辺を持つ（P 側には produces を書かない）。

---

## P-1: ノード受付・パース

<details><summary>⬡ P-1 · v0.1</summary>

```yaml
id: P-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: I-1
    ref_version: "0.4"
  - to: D-1
    ref_version: "0.4"
  - to: D-2
    ref_version: "0.4"
  - to: E-1
    ref_version: "0.4"
```
</details>

ノードファイル群を受け取り、YAMLフロントマターをパースして構造化ノードセットに変換する。
**入力**: I-1（ノードファイル群）・D-1（in-graph 集合）・D-2（著作済みノード）を消費（P→I/P→D）
**出力**: 構造化ノードセット（P-2 へ）
**トリガ**: E-1 に依存（P→E）

---

## P-2: RULE 検査

<details><summary>⬡ P-2 · v0.1</summary>

```yaml
id: P-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-5
    ref_version: "0.3"
  - to: I-2
    ref_version: "0.4"
  - to: I-3
    ref_version: "0.4"
  - to: I-4
    ref_version: "0.4"
```
</details>

構造化ノードセットに全 RULE（構造完結性 RULE-005〜008・ドリフト RULE-001/002/004/022・カバレッジ RULE-016〜019・検証層 RULE-006/020/021）を、3 軸抑制（scheduled/ステージ発火/suppress）を適用して評価し、違反ノードと違反内容を列挙する。
**入力**: P-1 からの構造化ノードセット、I-2（suppress 設定）・I-3（scheduled 設定）・I-4（ref_version 値）を消費（P→I）
**出力**: 違反リスト（P-4 へ）
**トリガ**: P-1 完了後に連続起動

---

## P-3: カバレッジ点検

<details><summary>⬡ P-3 · v0.1</summary>

```yaml
id: P-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-14
    ref_version: "0.3"
```
</details>

ノードセットの入力・出力・イベントの網羅性（孤児ノード・未駆動出力・未定義反応）と、SPEC×condition×TD の仕様カバレッジを確認する。
**入力**: P-1 からの構造化ノードセット
**出力**: カバレッジ穴リスト（P-4 へ）
**トリガ**: P-1 完了後に連続起動

---

## P-4: レポート生成

<details><summary>⬡ P-4 · v0.1</summary>

```yaml
id: P-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-25
    ref_version: "0.3"
```
</details>

RULE 違反リストとカバレッジ穴リストを深刻度順（ERROR→WARNING→INFO）に整列し、G#番号付きで整形して出力する。ERROR があれば終了コード 1 を返す。
**入力**: P-2 の違反リスト・P-3 のカバレッジ穴リスト
**出力**: O-1（RULE違反レポート）・O-2（カバレッジ点検結果）が P-4 に依存（O→P）
**トリガ**: P-2・P-3 完了後

---

## P-5: 設定ファイル読み込み

<details><summary>⬡ P-5 · v0.1</summary>

```yaml
id: P-5
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-21
    ref_version: "0.3"
  - to: I-5
    ref_version: "0.4"
  - to: E-1
    ref_version: "0.4"
```
</details>

`config.yaml` を読み込んで検証済み設定オブジェクト（current_phase・current_stage・phases・stages・must_link_to・must_be_linked_from・rule_activation・condition_vocab・trace_scope）に変換する。P-1/P-2/P-3 が参照する共有設定として提供する。
**入力**: I-5 を消費（P→I）
**出力**: 検証済み設定オブジェクト（P-1/P-2/P-3 へ）
**トリガ**: E-1 に依存（P→E・P-1 と並行または先行して実行）

---

## P-6: in-graph 集合決定

<details><summary>⬡ P-6 · v0.1</summary>

```yaml
id: P-6
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-24
    ref_version: "0.3"
  - to: I-5
    ref_version: "0.4"
  - to: I-6
    ref_version: "0.4"
  - to: E-1
    ref_version: "0.4"
```
</details>

trace_scope.include/exclude（I-5）と候補パス一覧（I-6）を照合し、in-graph ファイル集合（D-1）を決定する。
**入力**: I-5（trace_scope 設定）・I-6（候補パス一覧）を消費（P→I）
**出力**: D-1（in-graph ファイル集合）が P-6 に依存（D→P）
**トリガ**: E-1 に依存（P→E・P-5 と並行または直後）

---

## P-7: ノード著作プロセス

<details><summary>⬡ P-7 · v0.1</summary>

```yaml
id: P-7
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-26
    ref_version: "0.3"
  - to: I-7
    ref_version: "0.4"
  - to: I-8
    ref_version: "0.4"
  - to: E-3
    ref_version: "0.4"
```
</details>

仕様著者（ACTOR-1）がテンプレート（I-7）または著作エージェント（I-8）を用いてノードを著作し、ノードファイル（D-2）を生成する。
**入力**: I-7（テンプレート参照）・I-8（著作エージェント呼び出し）を消費（P→I）
**出力**: D-2（著作済みノードファイル）が P-7 に依存（D→P）
**トリガ**: E-3 に依存（P→E・著作要求）
