---
id: TR-gitgate-copilot-629-001-504868bc
title: Copilot固定PR base取り込み初回実装のローカル検証
design: TD-gitgate-copilot-629-001
implementation_commit: 504868bc2fbe68f18c01d63d4c15188b69cf9a6c
result: review_fix_required
log_ref: tests/logs/TD-gitgate-copilot-629-001-target-504868bc.txt
---

実装commit 504868bcのローカル検証。PR未公開でありPR CI結果ではない。

| 項目 | 実測 | ログ |
|---|---|---|
| 対象回帰 | 43 tests, OK（既存27＋新16） | `tests/logs/TD-gitgate-copilot-629-001-target-504868bc.txt` |
| asset_parity | exit 0、0 MISSING、既存heuristic stalenessあり | `tests/logs/TD-gitgate-copilot-629-001-asset-parity-504868bc.txt` |
| maintainability | exit 0、violations=0 accepted_debt=94、baseline変更なし | `tests/logs/TD-gitgate-copilot-629-001-maintainability-504868bc.txt` |
| guidance_sync | exit 0、check OK | `tests/logs/TD-gitgate-copilot-629-001-guidance-sync-504868bc.txt` |
| 全unit | ABORTED、SIGINT exit 130、PASSではない | `tests/logs/TD-gitgate-copilot-629-001-full-504868bc.txt` |
| 初回対象試行 | 43件中1失敗。0件unittestのPython exit code差に対するtest期待だけ修正 | `tests/logs/TD-gitgate-copilot-629-001-precommit-failed.txt` |

正常・衝突・abortの実Git3経路、およびrequest/branch/session drift、pending再登録・publish拒否、実runner失敗と成功0件、内容CAS、既存host境界を確認した。

独立レビューは共有ledger上のCopilot running entryがClaude差分fallbackをambiguous-runningにする退行を再現した。初回実装担当は是正しない。主文脈指示で旧commitの全unitを中断し、是正担当への引継ぎと最終版での全unit実行を優先する。途中結果を成功扱いしない。
