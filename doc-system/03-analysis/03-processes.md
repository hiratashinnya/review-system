---
version: "0.5.0"
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
    ref_version: "0.5"
  - to: D-1
    ref_version: "0.5"
  - to: D-2
    ref_version: "0.5"
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

<details><summary>⬡ P-2 · v0.2</summary>

```yaml
id: P-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-5
    ref_version: "0.3"
```
</details>

（P-2-1〜P-2-4 に責務を委譲）SPEC-5 の通過条件が揃った状態を確認する親プロセス。消費入力の明示は各子プロセスに移す。

---

### P-2-1: ドリフト・義務辺検査

<details><summary>⬡ P-2-1 · v0.1</summary>

```yaml
id: P-2-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-9
    ref_version: "0.3"
  - to: SPEC-11
    ref_version: "0.3"
  - to: SPEC-12
    ref_version: "0.3"
  - to: SPEC-13
    ref_version: "0.3"
  - to: I-4
    ref_version: "0.5"
  - to: E-1
    ref_version: "0.4"
```
</details>

P-1 の構造化ノードセットを受け取り、各辺の ref_version と参照先ファイル version の x.y を比較（RULE-004）し、DD/Q/PEND ノードの義務辺存在を検出（RULE-001/002/022）する。
**入力**: I-4（ref_version 値）を消費（P→I）
**出力**: ドリフト・義務辺違反リスト（P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

### P-2-2: 構造完結性検査

<details><summary>⬡ P-2-2 · v0.1</summary>

```yaml
id: P-2-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-6
    ref_version: "0.3"
  - to: SPEC-7
    ref_version: "0.3"
  - to: SPEC-8
    ref_version: "0.3"
  - to: I-2
    ref_version: "0.5"
  - to: I-3
    ref_version: "0.5"
  - to: E-1
    ref_version: "0.4"
```
</details>

グラフの構造的健全性を検証する。always_error（RULE-005/007）は suppress/scheduled を無視して発火。孤立（RULE-005）・存在しない ID（RULE-007）・必須辺欠如（RULE-006）・階層親不在（RULE-008）を検査する。
**入力**: I-2（suppress 設定）・I-3（scheduled 設定）を消費（P→I）
**出力**: 構造違反リスト（P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

### P-2-3: カバレッジ属性検査

<details><summary>⬡ P-2-3 · v0.1</summary>

```yaml
id: P-2-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-15
    ref_version: "0.3"
  - to: SPEC-16
    ref_version: "0.3"
  - to: I-2
    ref_version: "0.5"
  - to: I-3
    ref_version: "0.5"
  - to: E-1
    ref_version: "0.4"
```
</details>

SPEC・TD の condition 属性の存在と語彙、FR 配下の condition 網羅（normal 必須・failure/error 推奨）を検査する。condition 属性語彙（RULE-016）・FR の SPEC 網羅（RULE-017/018）・TD-SPEC condition 整合（RULE-019）を検査する。
**入力**: I-2（suppress 設定）・I-3（scheduled 設定）を消費（P→I）
**出力**: カバレッジ属性違反リスト（P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

### P-2-4: 検証層完結性検査

<details><summary>⬡ P-2-4 · v0.1</summary>

```yaml
id: P-2-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-17
    ref_version: "0.3"
  - to: SPEC-18
    ref_version: "0.3"
  - to: SPEC-19
    ref_version: "0.3"
  - to: I-2
    ref_version: "0.5"
  - to: I-3
    ref_version: "0.5"
  - to: E-1
    ref_version: "0.4"
```
</details>

検証層ノード（FND/TC/VERIFY/TR）の辺と属性の完結性を verification ステージ発火ルールで検査する。FND/TC/VERIFY の必須辺（RULE-006 verification）・TR の result/log_ref（RULE-020/021）を検査する。
**入力**: I-2（suppress 設定）・I-3（scheduled 設定）を消費（P→I）
**出力**: 検証層違反リスト（P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

## P-3: カバレッジ点検

<details><summary>⬡ P-3 · v0.2</summary>

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

（P-3-1: グラフ網羅性・P-3-2: 仕様カバレッジ計測 に分担）カバレッジ点検を担う親プロセス。

---

### P-3-1: グラフ網羅性点検

<details><summary>⬡ P-3-1 · v0.1</summary>

```yaml
id: P-3-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-29
    ref_version: "0.3"
  - to: SPEC-30
    ref_version: "0.3"
  - to: E-1
    ref_version: "0.4"
```
</details>

分析層ノード（I/O/D/P/E）の接続網羅性を確認する。未駆動出力（O に P依存辺なし）・未定義反応（E に P被依存辺なし）・孤立ノードをゼロにすることで価値経路の完全性を保証する（SPEC-29/30 は FR-3 配下の新規 SPEC）。
**入力**: P-1 からの構造化ノードセット
**出力**: グラフ網羅性穴リスト（P-4 へ）
**トリガ**: E-1 に依存（P→E）

---

### P-3-2: 仕様カバレッジ計測

<details><summary>⬡ P-3-2 · v0.1</summary>

```yaml
id: P-3-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-14
    ref_version: "0.3"
  - to: E-1
    ref_version: "0.4"
```
</details>

FR ごとに condition 軸（normal/boundary/failure/error）で SPEC と TD の充足状況を集計し、`--coverage` オプション実行時にカバレッジテーブルを出力する。
**入力**: P-1 からの構造化ノードセット
**出力**: カバレッジテーブル（P-4 へ）
**トリガ**: E-1 に依存（P→E）

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
    ref_version: "0.5"
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
    ref_version: "0.5"
  - to: I-6
    ref_version: "0.5"
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
    ref_version: "0.5"
  - to: I-8
    ref_version: "0.5"
  - to: E-2
    ref_version: "0.4"
```
</details>

仕様著者（ACTOR-1）がテンプレート（I-7）または著作エージェント（I-8）を用いてノードを著作し、ノードファイル（D-2）を生成する。
**入力**: I-7（テンプレート参照）・I-8（著作エージェント呼び出し）を消費（P→I）
**出力**: D-2（著作済みノードファイル）が P-7 に依存（D→P）
**トリガ**: E-2 に依存（P→E・著作要求）
