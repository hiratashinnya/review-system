---
id: TR-gitgate-copilot-629-001-r1-8fa8f70c
title: Copilot認可namespace是正の最終ローカル検証
design: TD-gitgate-copilot-629-001
implementation_commit: 8fa8f70cd2081f1f07b7ad745be6d53a2e0cfdb7
result: pass
log_ref: tests/logs/TD-gitgate-copilot-629-001-r1-target-8fa8f70c.txt
---

F-629-01を認可/dispatch namespaceの分離で是正した。認可は専用
`base_authorizations` のauthorized/revokedとして保存し、Claude dispatchのentriesと
lifecycleを共有しない。両collectionを原子的に保存し、operation CASとpending
publish fenceは両方を検査する。既存Claude live dispatchのfail-closeを維持する。

| 項目 | 最終commitの実測 | ログ |
|---|---|---|
| 対象回帰 | 50 tests / 72.548s / OK | `tests/logs/TD-gitgate-copilot-629-001-r1-target-8fa8f70c.txt` |
| asset_parity | exit 0、0 MISSING、既存heuristic stalenessあり | `tests/logs/TD-gitgate-copilot-629-001-r1-asset-parity-8fa8f70c.txt` |
| maintainability | exit 0、violations=0 accepted_debt=94、baseline変更なし | `tests/logs/TD-gitgate-copilot-629-001-r1-maintainability-8fa8f70c.txt` |
| guidance_sync | exit 0、check OK | `tests/logs/TD-gitgate-copilot-629-001-r1-guidance-sync-8fa8f70c.txt` |
| time_fixture | exit 0、violations=0 | `tests/logs/TD-gitgate-copilot-629-001-r1-time-fixture-8fa8f70c.txt` |
| 全unit | exit 0、2031 tests / 415.257s / OK (skipped=9) | `tests/logs/TD-gitgate-copilot-629-001-r1-full-8fa8f70c.txt` |

登録中/pending中/committed後/aborted後のClaude単一候補diff成功、各段階の実Claude
running存在時拒否を確認。通常dispatch writer後も認可/operationは保存される。
再登録は旧認可をrevokedにする。未登録・revoked・破損collectionは拒否する。
正常/衝突/abort、drift、pending再登録/publish、test失敗/0件、内容CAS、両host gateも
対象50件に含む。production各moduleは100行以内、worktree_ledgerとbaselineは無変更。

初回実装の43件成功、全unit ABORTED、0件runner期待失敗は旧TR/ログを保持する。
是正の最初の2試行では、継承fixtureの初期Claude setupがCopilot専用getterを呼び、
49件中21/50件中22のsetup errorとなった。テスト側の初期setup委譲を直した。
失敗ログは `tests/logs/TD-gitgate-copilot-629-001-r1-setup-failed-49.txt` と
`tests/logs/TD-gitgate-copilot-629-001-r1-setup-failed-50.txt` に保持した。
独立初回レビューとF-629-01は `tests/reports/REVIEW-gitgate-copilot-629-r1.md` と
`tests/reports/REVIEW-gitgate-copilot-629-r1-findings.md` に保持する。

karte Attempt1はfixedでclose。別担当のr2独立再レビューはcode/docs clean、
F-629-01 resolved、新findingなし。r2記録は `tests/reports/REVIEW-gitgate-copilot-629-r2.md` と
`tests/reports/REVIEW-gitgate-copilot-629-r2-findings.md` に保持する。ローカル検証であり
公開PR CIの結果ではない。push/PR公開・mergeは行っていない。

全unitは `python3 -m unittest discover -s tests/unit -q` を実行。local HTTP mock用
network許可を使い、外部live APIに依存しない。9 skipは既存suiteの環境依存条件である。
