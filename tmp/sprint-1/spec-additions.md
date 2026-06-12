## SPEC-29: グラフ網羅性点検の正常系（normal）

<details><summary>⬡ SPEC-29 · v0.1</summary>

```yaml
id: SPEC-29
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-3
    ref_version: "0.2"
```
</details>

**前提条件**: 全 I/O/D/P/E ノードが適切な接続を持つ（O→P・O→ACTOR・D→P・E→ACTOR・P→I/D/E の各依存辺、および I←P・D←P・E←P の被依存辺が揃っている）
**入力/トリガ**: 検証ツールがグラフ網羅性点検（P-3-1）を実行する
**期待動作**: 孤立ノード（RULE-005）・必須辺欠如（RULE-006 config の analysis 段接続）をゼロ件として通過させ、グラフが価値経路（VAL まで到達可能）と分析層接続を完全に満たすと判定する

---

## SPEC-30: 分析ノードの接続漏れ検出（failure）

<details><summary>⬡ SPEC-30 · v0.1</summary>

```yaml
id: SPEC-30
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-3
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に分析層ノード（I/O/D/P/E）が存在する
**入力/トリガ**: P-3-1 がグラフ網羅性を確認する際に、O に P への依存辺がない・E に P からの被依存辺がない・I に P からの被依存辺がないノードを検出する
**期待動作**: 未駆動出力（O→P 欠如）・未定義反応イベント（E←P 欠如）・未消費入力（I←P 欠如）を RULE-006 の config `activate_stage: analysis` 行の severity（error/warning）として報告する（SPEC-8 の一般則における分析層の特殊ケース）
