---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-e20b90b-ci-fail.txt
---

# 目的

Issue #452改訂契約を、bwrap/Codex CLIを備えない標準GitHub runnerでもpure unitが外部環境へ
依存せず検証できることを確認する。

# 前提・手順・期待結果

`tests/designs/TD-issue-start-452.md` version 6を適用し、PR #506 head `e20b90b`に対して
`python3 -m unittest discover -s tests/unit`を実行する。pure source/ledger/command負例は意図した
reasonまで到達し、installed executableのactive boundaryはoperational testとして区別されること。

## 実測

- ヘッダ: TD version 6 / 実装commit `e20b90b` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-10 UTC / GitHub Actions ubuntu-24.04, Python 3.14.7
- 結果: FAIL（1789 tests、22 failures、7 errors、15 skipped）
- ログ: `tests/logs/TD-issue-start-452-e20b90b-ci-fail.txt`
- 外部証拠: https://github.com/hiratashinnya/review-system/actions/runs/34493490224/job/102925911253
- 全件分類: bwrap実在検査へのpure test越境27件、installed Codex欠落1件、launch-control raw loaderのmanifest seam漏れ1件。別原因の失敗はない。
- 根本原因: manifest/intent consumerのpure fixtureがproduction executable検証を隔離せず、hostに偶然bwrap/Codexがある場合だけ成功していた。
- 対処: pure helperへ決定的executable evidence seamを適用し、専用security testsはdirectのまま維持する。installed Codex欠落はNOT_TESTEDとして扱い、skipを成功証拠にしない。
