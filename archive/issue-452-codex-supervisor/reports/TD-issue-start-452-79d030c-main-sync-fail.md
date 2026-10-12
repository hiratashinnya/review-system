---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-79d030c-main-sync-fail.txt
---

# 目的

Issue #452改訂契約について、Codex spawn binding退役、supervisor direct-exec縮小、durable
recovery、権限非対称、model-originated commandのmodel/API到達遮断を検証する。旧brokerまたは
未実装時ログを成功証拠にしない。

# 前提

- Claude transportはmanifest marker/worktree isolationを維持する。
- Codex正規経路はIssue専用worktreeのrepo supervisorだけである。
- `run|resume`の親入力はIssue、role、change-plan ID、fixer roundだけである。
- host control-planeとmodel command data-planeは別境界である。

# 手順と期待結果

`tests/designs/TD-issue-start-452.md` version 6 の手順1〜9を実行し、特にorigin/mainのIssue #491
process feature安全策とIssue #452 permission-profile preflightの意味保存統合を検査する。

# 残余リスク

TD version 6記載の残余リスクをそのまま適用する。

## 実測

- ヘッダ: TD version 6 / 実装commit `79d030c` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-10 JST / Codex test sandbox
- 結果: FAIL（292 tests、2 errors、12 skipped）
- ログ: `tests/logs/TD-issue-start-452-79d030c-main-sync-fail.txt`
- 根本原因: feature listのmaturity複数語を拒否する過剰な3-token限定と、feature unitが検査対象外のsocket境界まで到達するtest seam不足。
- 対処: parserをmain #491どおり3 token以上・先頭name・末尾stateへ戻し、unitではactive boundary probeをmockしてfeature preflightだけを隔離する。permission-profile実境界testは別testのまま維持する。
