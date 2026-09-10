---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-6ff2faa-main-sync-fail.txt
---

# 目的

Issue #452改訂契約と、origin/mainのIssue #491 process feature安全策の意味保存統合を検証する。

# 前提・手順・期待結果・残余リスク

`tests/designs/TD-issue-start-452.md` version 6をそのまま適用する。

## 実測

- ヘッダ: TD version 6 / 実装commit `6ff2faa` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-10 JST / Codex test sandbox
- 結果: FAIL（292 tests、1 error、12 skipped）
- ログ: `tests/logs/TD-issue-start-452-6ff2faa-main-sync-fail.txt`
- 当初仮説と反証: `--config`後置を疑ったが、CLI helpと前置/後置双方のmodel-free実測で後置も有効と確認したため棄却した。
- 根本原因: installed profile testの手組みcommandがproduction builderのrequired-disabled feature overrideを一件も含まない古いfixtureだった。
- 対処: production契約のrequired-disabled集合からfixture argsを導出する。production builderとの一致は別unitが集合全件を独立assertする。
