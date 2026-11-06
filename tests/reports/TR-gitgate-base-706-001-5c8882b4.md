---
id: TR-gitgate-base-706-001-5c8882b4
title: gitgate-base-integration/2.0 の対象テストと整合検査
design: TD-gitgate-base-706-001
implementation_commit: 5c8882b4faf4007149befb6c20845a8d7954e0cb
result: pass
log_ref: tests/logs/TD-gitgate-base-706-001-target-5c8882b4.txt
---

Claude Code (AI) による検証記録。2026-10-31、レビュー是正（回復手順の実行可能化・退避 tar の明記・
退役 Codex wrapper へのリンク除去）を commit した `5c8882b4faf4007149befb6c20845a8d7954e0cb` を
凍結したまま実行した（commit-before-test）。本 TR とログの追加 commit はコード・文書を変えない。

以下ログ名の接頭辞は `tests/logs/TD-gitgate-base-706-001-`、接尾辞は `-5c8882b4.txt`。
各ログは対象 HEAD、正確な command、開始 UTC、exit code、経過秒を保持する。

| 検証 | 実測結果 | ログ種別 |
|---|---|---|
| `python3 -m unittest tests.unit.test_base_integration tests.unit.test_base_integration_rejections tests.unit.test_base_integration_gate -q` | 28 tests / 170.802s / OK、exit0 | target |
| `python3 -m unittest tests.unit.test_governance_sync -q` | 20 tests / 0.133s / OK、exit0 | governance-sync |
| `python3 -m guidance_sync check` | exit0、check OK | guidance-sync |
| `python3 -m asset_parity check` | exit0、49 assets、0 MISSING、14 staleness flags | asset-parity |
| `python3 -m maintainability_lint check` | exit0、violations=0、accepted_debt=77 | maintainability-lint |

対象 28 件は TD-gitgate-base-706-001 の対応表に挙げたテスト（衝突解消・確定、衝突なし確定と no-change、
abort の退避と復帰、記録だけ残った場合の回復、primary worktree・サブディレクトリ実行、ロール別 gate、
protected path の取り込みと衝突、明示 stage と stage し忘れ、`--test-module` 不在、対象・pending 中の拒否、
通常 commit の fence、API 障害）を含む3モジュールの全件である。skip は無い。
target ログの stdout/stderr にある Git のエラー文は負例テストの出力であり、最終結果は上表の OK である。

外部 live API・LLM は呼んでいない（偽 PR API と一時 bare remote のみ）。全 unit（`discover`）と
CI の他 job は実行しておらず、それらの合格は主張しない。今回の実行に失敗・中断した試行は無い。
