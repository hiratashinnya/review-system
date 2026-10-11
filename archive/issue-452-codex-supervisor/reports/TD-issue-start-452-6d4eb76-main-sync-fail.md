---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-6d4eb76-main-sync-fail.txt
---

# 目的

Issue #452改訂契約と、origin/mainのIssue #491 process feature安全策の意味保存統合を検証する。

# 前提・手順・期待結果・残余リスク

`tests/designs/TD-issue-start-452.md` version 6をそのまま適用する。

## 実測

- ヘッダ: TD version 6 / 実装commit `6d4eb76` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-10 JST / Codex test sandbox
- 結果: FAIL（292 tests、1 error、13 skipped）
- ログ: `tests/logs/TD-issue-start-452-6d4eb76-main-sync-fail.txt`
- 根本原因: 実catalogで観測してrequired-disabled化した2名を、unit fixture生成元の観測名台帳へ反映していなかった。
- 対処: 2名をrequired-disabledに残したまま観測名台帳へも追加する。true/absentを拒否する独立assertは維持する。
