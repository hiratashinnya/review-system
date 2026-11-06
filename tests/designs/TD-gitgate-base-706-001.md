---
id: TD-gitgate-base-706-001
title: PR base 取り込みを責務に絞った gitgate-base-integration/2.0
---

目的: Issue #706 の Acceptance criteria を検証する。前提は実 bare remote、PR head を checkout した
linked worktree または primary worktree、読取専用の偽 PR API。ロール・dispatch 台帳・登録・
テスト実行は一切用意しない。

| AC | ケース | テスト（`tests/unit/`） |
|---|---|---|
| 1 | 衝突→解消→確定（unittest 不実行・2親） | `test_base_integration.IntegrationFlowTests.test_conflict_resolve_continue_without_tests_or_dispatch` |
| 1 | 正常（衝突なし）→確定→no-change | `test_base_integration.SimpleMergeTests.test_protected_paths_incoming_merge_and_no_change` |
| 1, 8 | abort（API 無し）で編集を退避し元 HEAD へ復帰・再開始 | `test_base_integration.IntegrationFlowTests.test_abort_saves_edits_restores_head_without_api` |
| 8 | gitgate 外で merge が終わった後の記録の回復 | `test_base_integration.IntegrationFlowTests.test_abort_clears_stale_record_after_merge_ended_outside` |
| 2 | dispatch 無し・primary worktree・サブディレクトリからの実行 | `test_base_integration.IntegrationFlowTests.test_primary_worktree_checkout_can_integrate`・`test_subdirectory_cwd_resolves_to_checkout_root` |
| 2, 3 | pipeline 外（主文脈・general-purpose 等）と issue-fixer は gate を通過 | `test_base_integration_gate.BaseIntegrationGateTests.test_fixer_and_callers_outside_pipeline_are_allowed` |
| 3 | pipeline 内の fixer 以外（implementer・reviewer 等）は拒否 | `test_base_integration_gate.BaseIntegrationGateTests.test_pipeline_roles_other_than_fixer_are_denied` |
| 4 | 全 protected path の incoming 変更を取り込み | `test_base_integration.SimpleMergeTests.test_protected_paths_incoming_merge_and_no_change` |
| 4 | 全 protected path の衝突を解消・確定 | `test_base_integration.ProtectedConflictTests.test_conflicting_protected_paths_can_be_resolved` |
| 5 | 周辺 tracked 修正・新規ファイル・生成物を `gitgate add` で明示 stage して確定 | `test_base_integration.IntegrationFlowTests.test_extra_tracked_new_and_generated_files_are_committed_when_staged` |
| 5 | stage し忘れは確定せず作業を保持 | `test_base_integration.IntegrationFlowTests.test_unstaged_leftovers_stop_and_keep_pending_work` |
| 6 | `--test-module` と登録 verb は存在しない | `test_base_integration.IntegrationFlowTests.test_continue_cli_rejects_test_module_option` |
| 7 | default branch を取り込み先にする | `test_base_integration_rejections.TargetRejectionTests.test_default_branch_as_target_is_rejected` |
| 7 | 別 PR・別 head・別 base・別 repository・fork | `test_base_integration_rejections.TargetRejectionTests.test_wrong_pr_head_base_and_repository_are_rejected`・`test_expected_head_must_match_checkout_and_base_must_match_fetch` |
| 7 | 解消中の base 移動・PR retarget | `test_base_integration_rejections.PendingRejectionTests.test_base_moved_or_pr_retargeted_during_resolution_is_rejected` |
| 7 | 未解消 index（マーカー残り・記録外の unmerged） | `test_base_integration.IntegrationFlowTests.test_unresolved_conflict_markers_are_rejected`・`test_base_integration_rejections.PendingRejectionTests.test_unmerged_index_outside_record_is_rejected` |
| 7 | 異なる Git 操作との競合・二重開始・gitgate 外の merge | `test_base_integration_rejections.TargetRejectionTests.test_dirty_detached_and_competing_operations_are_rejected`・`PendingRejectionTests.test_competing_git_operation_or_moved_head_is_rejected`・`test_double_start_is_rejected`・`ForeignMergeTests.test_merge_not_started_by_gitgate_is_never_continued_or_aborted` |
| 7 | PR merge・auto-merge・raw git merge は全ロール拒否 | `test_base_integration_gate.BaseIntegrationGateTests.test_pr_merge_auto_merge_and_raw_merge_stay_denied_for_every_role` |
| 8 | 進行中の通常 commit を拒否・API 障害で状態を残さない | `test_base_integration_rejections.PendingRejectionTests.test_ordinary_commit_is_fenced_while_pending`・`TargetRejectionTests.test_api_failure_leaves_clean_tree_without_record` |
