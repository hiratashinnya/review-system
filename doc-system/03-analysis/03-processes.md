---
version: "0.3.0"
---
# 論理プロセス

> **型**: P ／ **必須上流**: SPEC（refines ✅）
> P 側に `kind: consumes`（I→P と書かない）。E 側が `kind: triggers` で P を起動する。

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
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: I-1
    kind: consumes
    status: pending
    ref_version: "0.3"
  - to: O-3
    kind: consumes
    status: pending
    ref_version: "0.3"
```
</details>

ノードファイル群を受け取り、YAMLフロントマターをパースして構造化ノードセットに変換する。
**入力**: I-1 を消費（consumes）、O-3（in-graph ファイル集合）を消費（consumes）
**出力**: 構造化ノードセット（P-2 へ）
**トリガ**: E-1 から起動（triggers）

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
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: I-2
    kind: consumes
    status: pending
    ref_version: "0.3"
  - to: I-3
    kind: consumes
    status: pending
    ref_version: "0.3"
  - to: I-4
    kind: consumes
    status: pending
    ref_version: "0.3"
```
</details>

構造化ノードセットに全 RULE（構造完結性 RULE-005〜008・ドリフト RULE-001〜004・カバレッジ RULE-015〜019・検証層 RULE-009〜013/020/021）を、3 軸抑制（scheduled/stage/suppress）を適用して評価し、違反ノードと違反内容を列挙する。
**入力**: P-1 からの構造化ノードセット、I-2（suppress 設定）・I-3（scheduled 設定）・I-4（ref_version 値）を消費（consumes）
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
    kind: refines
    status: pending
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
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: O-1
    kind: produces
    status: pending
    ref_version: "0.3"
  - to: O-2
    kind: produces
    status: pending
    ref_version: "0.3"
```
</details>

RULE 違反リストとカバレッジ穴リストを深刻度順（ERROR→WARNING→INFO）に整列し、G#番号付きで整形して出力する。ERROR があれば終了コード 1 を返す。
**入力**: P-2 の違反リスト・P-3 のカバレッジ穴リスト
**出力**: O-1（RULE違反レポート）・O-2（カバレッジ点検結果）を生成（produces）
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
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: I-5
    kind: consumes
    status: pending
    ref_version: "0.3"
```
</details>

`config.yaml` を読み込んで検証済み設定オブジェクト（current_phase・current_stage・phases・stage_scope.disable・condition_vocab・trace_scope）に変換する。P-1/P-2/P-3 が参照する共有設定として提供する。
**入力**: I-5 を消費（consumes）
**出力**: 検証済み設定オブジェクト（P-1/P-2/P-3 へ）
**トリガ**: E-1 から起動（P-1 と並行または先行して実行）

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
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: I-5
    kind: consumes
    status: pending
    ref_version: "0.3"
  - to: I-6
    kind: consumes
    status: pending
    ref_version: "0.3"
  - to: O-3
    kind: produces
    status: pending
    ref_version: "0.3"
```
</details>

trace_scope.include/exclude（I-5）と候補パス一覧（I-6）を照合し、in-graph ファイル集合（O-3）を決定する。
**入力**: I-5（trace_scope 設定）・I-6（候補パス一覧）を消費（consumes）
**出力**: O-3（in-graph ファイル集合）を生成（produces）
**トリガ**: E-1 から起動（P-5 と並行または直後）

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
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: I-7
    kind: consumes
    status: pending
    ref_version: "0.3"
  - to: I-8
    kind: consumes
    status: pending
    ref_version: "0.3"
  - to: O-4
    kind: produces
    status: pending
    ref_version: "0.3"
```
</details>

仕様著者（ACTOR-1）がテンプレート（I-7）または著作エージェント（I-8）を用いてノードを著作し、ノードファイル（O-4）を生成する。
**入力**: I-7（テンプレート参照）・I-8（著作エージェント呼び出し）を消費（consumes）
**出力**: O-4（著作済みノードファイル）を生成（produces）
**トリガ**: E-3 から起動（著作要求）
