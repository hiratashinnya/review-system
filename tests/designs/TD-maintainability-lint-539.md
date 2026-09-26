---
id: TD-maintainability-lint-539
version: 1
condition: boundary
---
# 目的

Issue #539 の流入 role contract と流出 `maintainability_lint` が、オーナー指定4原則を
守りやすく破りにくい機構として働くことを確認する。

# 前提

- 対象は `review_system/` と含有されない汎用ハーネスの Python 実装。
- 既存負債は `maintainability_lint/baseline.json` に exact snapshot として固定する。
- 命名の意味品質は機械推測せず、3 role の review checklist で確認する。

# 手順

1. 合成 tree で100/101行、3/4行コメント、data/logic class 同居の境界を検査する。
2. exact baseline、違反編集、負債解消後の stale baseline を検査する。
3. 実 repository を committed baseline で検査する。
4. 3 role contract に4原則と lint 実行契約が存在することを検査する。
5. `python3 -m unittest tests.unit.test_maintainability_lint -v` を実行する。

# 期待結果

- 境界内は通り、境界超過、新規同居、baseline からの増加・編集・stale entry は失敗する。
- 実 repository は既存負債を報告しつつ violation 0 で終了する。
- 3 role すべてが流入 checklist を持つ。
