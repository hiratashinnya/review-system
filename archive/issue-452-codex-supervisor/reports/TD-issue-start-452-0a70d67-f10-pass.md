---
id: TD-issue-start-452
version: 6
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-0a70d67-f10-pass.txt
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
9. 修正commit後、host境界でfocused native-alias probeと関連supervisor/profile/gate/ledger testsを実行する。

# 残余リスク

nested Codexがmodel到達失敗前にlocal thread recordを作る可能性は受容する。ただし成功証拠に数えず、
listener request 0と到達失敗を証拠とする。same-UIDの非協調host processによるprivate control state外乱は
既存threat boundary外とする。

## 実測

- ヘッダ: TD version 6 / implementation commit `0a70d67a026a33e58541c0f6ebc0a39495cc7a70` / prompt template version: repository revision / baseline content hash: repository revision / 2026-09-10T09:00:50Z / Linux 6.18.33.2-microsoft-standard-WSL2 x86_64, Python 3.12.3, Codex CLI 0.153.4, bubblewrap 0.9.0
- ログ: `tests/logs/TD-issue-start-452-0a70d67-f10-pass.txt`
- 結果: host境界のfocused 3件は全PASS。関連261件はPASS、明示skip 9件。
- skip評価: 9件は退役済みCodex spawn/blocker評価経路の明示skipであり、F-452-10対象のactive native-alias probe、installed Codex matrix、`--version`、`app-server`はいずれも実行されPASSした。
- 境界確認: production `_ro_bind_source` validator、child `PATH=/usr/bin:/bin`、Node/install/auth/runtime/network denyは変更していない。fixtureはnative sourceから`/run/issue-supervised/codex`へのexact read-only alias bindを要求し、installed probeもそのaliasを保持する。
- 証拠区分: 本TRだけを修正後PASS証拠とし、`a9f9f51`および`96c904d`のFAIL TR/logは失敗履歴として保持する。
