---
id: TC-triage-001
version: 1.0
---
# 検証・参照除外・仕分け（P4 / S1・S2）

> 対象：`review_system.core.triage`（[02 P4](../../docs/process/02-decomposition.md)・[13 S1/S2](../../docs/requirements/13-stabilization.md)）。安全側デフォルトの境界を厚く。

## 目的
- **S1**：パック外 rule_id・自己申告は **❓未分類へ退避**（crash も silent-drop もしない／取りこぼしゼロ）。
- 参照集合の指摘は除外（参照は評価しない）。
- 仕分け：`determinism×severity→ポリシー→mode`。**S2**：未宣言/matrix 欠落は **🤖 にしない＝HUMAN_ONLY** に倒す。

## 手順
`python -m unittest -v tests.unit.test_triage`

## 期待結果
| # | 対象 | 入力 | 期待 |
|---|---|---|---|
| 1 | validate | pack に在る rule_id | valid に入る |
| 2 | validate(S1) | pack に無い rule_id | ❓未分類へ（crash しない） |
| 3 | validate 保存則 | valid数+未分類数 = 入力 finding 数 | 一致（取りこぼしゼロ） |
| 4 | exclude_reference | location.file ∈ 参照集合 | 除外される |
| 5 | exclude_reference エッジ | 同名・別ディレクトリ | 除外**されない**（パスで判定） |
| 6 | triage | deterministic×error＋policy=auto_log_only | **AUTO**（🤖） |
| 7 | triage | tradeoff＋policy=auto_suggest | **APPROVE**（✋） |
| 8 | triage | judgment＋policy=human_only | **JUDGE**（💬） |
| 9 | triage(S2) | rule_id のメタが無い | **JUDGE/HUMAN_ONLY**（🤖 にしない） |
| 10 | triage(S2) | policy matrix が当該を持たない | **HUMAN_ONLY**（自動適用を生まない） |
| 11 | triage override | policy overrides に rule_id | override の mode が勝つ |
</content>
