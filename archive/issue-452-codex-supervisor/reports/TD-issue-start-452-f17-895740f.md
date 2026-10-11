---
id: TD-issue-start-452-f17
version: 1
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-f17-895740f.txt
---

# 目的

F-452-24のdiagnosis_ready後・karte登録WAL前crashから、canonical runの非破壊拒否と同一thread resumeによるAttempt一件収束を、production execute_launch_request経路で検証する。

# 前提

- owner-created canonical launch entryとround 2のopen finding、host ledgerを用意する。
- 初回診断runnerはJSONL identity/terminalとproposalを返し、登録直前にcrashを注入する。
- canonical runはbridge state diagnosingまたはregisteringの復旧状態を変更せず、resumeだけが中央karteを更新する。

# 手順・期待結果

1. `execute_launch_request(mode="run")` の診断完了後、`register_diagnosis` 最初のWAL commit前にcrashを注入する。
2. latest `diagnosis_ready` と bridge `diagnosing` を確認し、canonical runを再試行する。
3. canonical runがrunnerを起動せず、ledger bytesを不変のまま `RESUME_REQUIRED` で拒否することを確認する。
4. 同一threadのcanonical resumeを実行し、診断登録・修正実行が成功し、中央karte Attemptが一件に収束することを確認する。
5. bridge/supervisor/worktree ledger回帰とfull unittest、coverage HTMLを実行する。

## TC

`tests/unit/test_codex_karte_bridge.py::KarteBridgeTests.test_canonical_run_during_diagnosis_is_non_destructive_and_resume_converges` および既存 bridge/supervisor/worktree ledger tests。

## 実測

- 実装commit: 895740f
- 実行日: 2026-09-15 Asia/Tokyo
- F-452-24 focused: 1 test PASS、skip 0
- bridge/supervisor/worktree regression: 172 tests PASS、skip 4
- full unit: 1807 tests PASS、skip 9
- coverage: TOTAL 85%、`issue_start/codex_karte_bridge.py` 88%、`issue_start/codex_supervisor_workspace.py` 84%
- HTML: `htmlcov/index.html` 生成済み（未commit）
- F-452-24: canonical run runner未起動、ledger byte不変、`RESUME_REQUIRED`、同一thread resume succeeded、中央 Attempt 1件
