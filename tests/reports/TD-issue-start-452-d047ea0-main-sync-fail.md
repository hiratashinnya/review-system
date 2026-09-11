---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-d047ea0-main-sync-fail.txt
---

# 目的

Issue #452改訂契約と、origin/mainのIssue #491 process feature安全策の意味保存統合を検証する。

# 前提・手順・期待結果・残余リスク

`tests/designs/TD-issue-start-452.md` version 6をそのまま適用する。

## 実測

- ヘッダ: TD version 6 / 実装commit `d047ea0` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-10 JST / Codex test sandbox
- 結果: FAIL（292 tests、2 errors、12 skipped）
- ログ: `tests/logs/TD-issue-start-452-d047ea0-main-sync-fail.txt`
- 根本原因1: fixture補正patchの同形箇所への誤適用により、別testに未定義変数展開が入った。
- 根本原因2: 0.153.4実catalogのmain snapshot外active feature `in_app_local_automation` / `sleep_tool`を未知process能力検査が拒否した。catalog stateとinstalled binary registry（in-app機能群／ExtensionItem Sleep/tool群）をmodel-freeで確認した。
- 対処: 誤適用を除去し、2 featureはknown allowへ追加せずrequired-disabled集合へ追加する。
