---
version: "0.1.0"
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
    ref_version: "0.1"
  - to: I-1
    kind: consumes
    status: pending
    ref_version: "0.1"
```
</details>

ノードファイル群を受け取り、YAMLフロントマターをパースして構造化ノードセットに変換する。
**入力**: I-1 を消費（consumes）
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
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

構造化ノードセットに全 RULE を適用し、違反ノードと違反内容を列挙する。
**入力**: P-1 からの構造化ノードセット
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
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

ノードセットの入力・出力・イベントの網羅性（孤児ノード・未駆動出力・未定義反応）を確認する。
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
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: O-1
    kind: produces
    status: pending
    ref_version: "0.1"
  - to: O-2
    kind: produces
    status: pending
    ref_version: "0.1"
```
</details>

RULE 違反リストとカバレッジ穴リストをG#番号付きで整形し、レポートとして出力する。
**入力**: P-2 の違反リスト・P-3 のカバレッジ穴リスト
**出力**: O-1（RULE違反レポート）・O-2（カバレッジ点検結果）を生成（produces）
**トリガ**: P-2・P-3 完了後
