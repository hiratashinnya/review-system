---
id: TD-maintainability-lint-539
version: 1
condition: boundary
result: PASS
log_ref: tests/logs/TD-maintainability-lint-539-80306b8.txt
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

## 実測

- ヘッダ: TD version 1 / implementation commit `80306b8` / prompt template N/A /
  criteria content hash N/A / 2026-09-26 / Codex CLI sandbox
- 結果: 13 tests、PASS。
- `python3 -m maintainability_lint check`: violation 0、accepted debt 137。
- 全 unit suite は2033 tests中、差分外の既存 Codex 環境依存で3 failures＋1 error、skip 9。
  failing source/test files は `origin/main...80306b8` で変更なし。詳細は PR 本文に記録する。
- coverage: 85%（9464 statements、1419 missed）。`htmlcov/index.html` を生成済みで未追跡。
