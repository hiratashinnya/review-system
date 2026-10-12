---
id: TD-issue-start-452
version: 6
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-a9f9f51-formal-fail.txt
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

1. manifest、hook、module inventoryを検査する。
2. unavailable Codex spawn transportを副作用なく拒否する。
3. issuer済みcanonical entryと4入力をsupervisorへ渡す。
4. direct commandとnative single-file aliasを構築する。
5. model/APIを使わないactive/negative probeで、worktreeだけを許可しruntime/auth/Codex install tree/networkを拒否する。
6. fake JSONL/process runnerでrun/resume/crashを検証する。
7. Popen直前race matrixとreservation lockを検証する。
8. protected patchとpublish state machineを検証する。
9. 実装後の差分を含むcheckoutでunit/full coverageを実行する。

# 残余リスク

nested Codexがmodel到達失敗前にlocal thread recordを作る可能性は受容する。ただし成功証拠に数えず、
listener request 0と到達失敗を証拠とする。same-UIDの非協調host processによるprivate control state外乱は
既存threat boundary外とする。

## 実測

- ヘッダ: TD version 6 / implementation commit `a9f9f51a63fcb2c6379cb2f3e0b5021610026a62` / prompt template version: repository revision / baseline content hash: repository revision / 2026-09-10T00:20:17Z / Linux 6.18.33.2-microsoft-standard-WSL2 x86_64, Python 3.12.3, Codex CLI 0.153.4, bubblewrap 0.9.0
- ログ: `tests/logs/TD-issue-start-452-a9f9f51-formal-fail.txt`
- 結果: formal full testの2件をhost境界でfocused再現した。1 error、1 failure。これはFAIL履歴であり完了証拠ではない。
- 根本原因候補: (1) synthetic preflight fixtureがproductionのnative single-file alias bindを構築していない。(2) runtime probeがproduction command内のnative aliasをnpm launcherへ差し替える一方、nodeとinstall treeを意図的に非mountとしている。
- 対処方針: current production contractと実installed Codex evidenceを照合し、production境界を弱めずstale fixtureだけを是正する。修正commit後に別TR/logでPASSを記録する。
