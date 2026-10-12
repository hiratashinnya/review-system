---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f39186e-ci-fail.txt
---

# 目的

Issue #452改訂契約を、bwrap/Codex CLIを備えない標準GitHub runnerでもpure unitが外部環境へ
依存せず検証できることを、round 17修正後の実装に対して確認する。

# 前提・手順・期待結果

`tests/designs/TD-issue-start-452.md` version 6を適用し、PR #506 head `f39186e`に対して
`python3 -m unittest discover -s tests/unit`を実行する。pure launch-intent testは決定的な
executable-evidence seamを通り、本来のcanonical control stateとlive Gitのassertionへ到達すること。

## 実測

- ヘッダ: TD version 6 / 実装commit `f39186e` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-11 UTC / GitHub Actions ubuntu-24.04, Python 3.14.7
- 結果: FAIL（1789 tests、2 errors、17 skipped）
- ログ: `tests/logs/TD-issue-start-452-f39186e-ci-fail.txt`
- 外部証拠: https://github.com/hiratashinnya/review-system/actions/runs/34541663123/job/103085452899
- 全件分類: 2件とも`CodexLaunchIntentTests`の`load_launch_intent`直呼びが既存の決定的evidence seamを迂回し、runnerにない`/usr/bin/bwrap`の検査で停止した。別原因の失敗はない。
- 根本原因: round 17で共通`load()` helperへseamを適用したが、child cwdとmock呼出し検査を個別に組む2テストがhelperを使わないまま残った。
- 対処: 2テストだけに既存seamを局所適用し、host executable検査へ到達した場合は環境にbwrapがあっても必ず失敗するsentinelを併置する。production validator/profile/denyとdirect security testsは変更しない。
