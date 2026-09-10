---
id: TD-issue-start-452
version: 6
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-dfacef6-r17-pass.txt
---

# 目的

Issue #452 PR #506のF-452-13/F-452-14是正後に、pure launch-intent unitのhost依存がなく、
executable security境界とrole asset同期が弱まっていないことを確認する。

# 前提・手順・期待結果

`tests/designs/TD-issue-start-452.md` version 6を適用する。実装をcommitしてからfocused unit、
asset parity、full unitを実行し、全テスト成功、mirror欠落ゼロ、pure helper外のsecurity専用test成功を
観測する。installed tool欠落によるskipはNOT_TESTEDであり成功証拠には数えない。

## 実測

- ヘッダ: TD version 6 / 実装commit `dfacef6` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-11 JST / local Codex test sandbox
- focused: 128 PASS、9 skipped、failure/error 0
- asset parity: 39 assets、0 MISSING、13 informational stale flags
- full unit: 1789 PASS、9 skipped、failure/error 0
- skip内訳: 9件すべてIssue #452で退役したlegacy Codex spawn/prepare transport。installed Codex testはこのhostでは実行してPASSした。
- seam境界: owner/mode、path/digest/version再検査、NSS/group fail-close、installed Codexの専用testがpure helper外でPASSした。
- NOT_TESTED規律: installed Codexがない環境では専用testだけを具体的reason付きskipとし、そのskipは成功証拠に数えない。既存の実host skip-0 permission-profile matrixをpositive evidenceとして維持する。
- ログ: `tests/logs/TD-issue-start-452-dfacef6-r17-pass.txt`
