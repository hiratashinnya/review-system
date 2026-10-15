---
id: TR-gitgate-copilot-629-001-integration-f2a968b6
title: PR640 main統合後のローカル再検証
design: TD-gitgate-copilot-629-001
implementation_commit: f2a968b6cf78d0ca54ac1e45c167bb706a91615c
result: pass
log_ref: tests/logs/TD-gitgate-copilot-629-001-integration-full-f2a968b6.txt
---

Codex AI agentによる検証記録。2026-10-14、統合済みcode/docsを凍結したまま検証した。
オーナー承認の今回限定例外の範囲と固定取り込み手順は
`.ai/rationale/gitgate-copilot-base-integration-629.md` に保持する。

検証対象は `f2a968b6cf78d0ca54ac1e45c167bb706a91615c`、親列は厳密に
`[dd78c17a2430304f6738826dc80353e8a24ed61a, d5ede8370a8cc39745c172c0e7dbfbedabee132b]`、
treeは `8962e8bbdcd43a0188543dec127dd81336ce4199`。
main進行後の追加取り込み、rebase、force、PR mergeは実行していない。

以下ログ名の接頭辞は `tests/logs/TD-gitgate-copilot-629-001-integration-`、
接尾辞は `-f2a968b6.txt`。各実行ログは対象HEAD、正確なcommand、開始UTC、exitを保持する。

| 検証 | 実測結果 | ログ種別 |
|---|---|---|
| `python3 -m unittest tests.unit.test_base_copilot tests.unit.test_base_integration -q` | 50 tests / 57.347s / OK、exit0 | target |
| `python3 -m unittest discover -s tests/unit -q` | 2083 tests / 376.927s / OK (skipped=10)、exit0 | full |
| `python3 -m asset_parity check` | exit0、41 assets、0 MISSING、18 heuristic staleness flags | asset-parity |
| `python3 -m maintainability_lint check` | exit0、violations=0、accepted_debt=94 | maintainability-lint |
| `python3 -m time_fixture_lint check` | exit0、violations=0 | time-fixture-lint |
| `python3 -m guidance_sync check` | exit0、check OK | guidance-sync |
| `python3 -m model_policy check` | exit0、check OK | model-policy |
| 親列/tree/sourcehash/上流bytes比較 | 全一致、exit0 | integrity |
| skip内訳の読取と動的skip単独確認 | 退役Codex経路の固定skip9件、時刻条件skip1件 | skip-inventory |

対象50件は正常/衝突/abort、drift、再登録、pending publish fence、runner失敗・0件、
CAS、Copilot各段階のClaude fallbackと本物dispatch拒否を含む。
全unitには新mainのguidance_sync/contract_split/model_policy/asset_parity関係も含まれる。
全unitの10skipは9件の退役経路と、22時台実行による
`RateLimitHookTests.test_future_reset_today_is_used_as_is` の
`near end of day; +2h may cross midnight` である。後者は単独再実行でskip理由を確認した。
全unit stdout/stderrにある不正入力やrevertのエラー文は負例テストの出力であり、
最終unittest結果は上表のOKである。今回のテスト実行に失敗・中断試行はない。
旧版43件/2031件や旧中断・setup失敗記録は旧TR/ログに保持し、今回の成功と混同しない。

local HTTP mockに必要なnetwork許可で実行し、外部live APIやLLMを呼んでいない。
今回の担当モデルは既存session継承であり、系統/層の新選択・resolved ID生成はない。
正式 `model_policy check` が停止agent templateとtracked-runtime検査を包含する。
`.github/workflows/tests.yml` と `asset-parity.yml` の新model-policyチェックを確認した。
これは対象範囲のローカル検証であり、全CI job（pyright、Jev等）の実行やPR CI合格を主張しない。

model_policy/、asset_parity/、`.ai/model-policy.json` の全24fileは固定mainとbytes一致。
`issue_start/worktree_ledger.py` と `maintainability_lint/baseline.json` は取り込み前headと無変更。
Copilot原稿SHA256は `b0a5933ae86454289a0a3fd5c08597fdf5706848c16e357b2ed20b6628469abb`、
生成instructions markerも一致する。検証担当はcode/docs/生成物を編集していない。

独立code/docsレビューはclean、新findingなし、F-629-01 resolved維持。
報告は `REVIEW-gitgate-copilot-629-integration-f2a968b6.md` と同名 `-findings.md` を参照。
このレビューはcode/docsと統合を対象とし、今回完成した全unit/TR/証跡commitの追確認は待ちである。
本記録作成時は追加push・外部PR本文更新とも未実施。後続証跡commitはcode/docsを変えず、
保存ログ/TR/レビュー記録のみを追加する。

完成証跡commit `bc0a9eba86d1a19428763eacd7fa5bea749cd404` に対する独立追加確認も完了し、
clean、新findingなし、F-629-01 resolved維持。全unit/5checks/対象50件/skip内訳/
TR/PR草稿を照合した報告は `REVIEW-gitgate-copilot-629-integration-evidence-f2a968b6.md`。
code/docsはf2の凍結を維持する。本追記時も追加pushと外部本文更新は未実施。
