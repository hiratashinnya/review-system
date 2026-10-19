# IT-TC-655 issue_start — 検査を呼ぶ経路の集約診断と識別子の結合テストケース

- 作成：ac-designer（Claude Code (AI)）／TD：[IT-TD-655](IT-TD-655.md)。fixture F0 は [ST-TC-655](../../../codex_worktree_exec/verify/designs/ST-TC-655.md) の定義。
- 本書はケース仕様である。各ケースは、工程 2a（test_design）で test-writer が Red の実テストとして `tests/issue_start/` に置く（一次記録は Issue #655 本文 Scope 1 のオーナー決定（2026-10-18）。test-writer の契約文言に対するオーナー承認の例外であることは [ST-TD-655](../../../codex_worktree_exec/verify/designs/ST-TD-655.md) §1。配置は `.ai/agents/creation-stage-contract.md:44`）。既存の補助（`tests/unit/test_phase_dispatch_binding.py`・`test_readonly_workspace.py`・`test_legacy_pr_rereview.py`）の fixture 構成を再利用してよい。
- 判定時点：[ST-TC-655](../../../codex_worktree_exec/verify/designs/ST-TC-655.md) 冒頭の判定時点の規則の (2)（merge 後に本 PR の `mergeCommit` の OID で判定し、その OID を ST-TR に記録する）による。

| TC | TD | 前提・手順 | 期待結果（合格条件） |
|---|---|---|---|
| IT-TC-655-IS-01-1 | IS-01 | 既存の正当な phase binding・approval を持つ作業面に C0・C3・C6 を各2件置き、`validate_phase_dispatch` を呼ぶ | `IssueStartError`、識別子 `ISSUE_START_PHASE_BINDING_INVALID`。detail に C0・C3・C6 の識別子と各件数2 |
| IT-TC-655-IS-02-1 | IS-02 | 正当な source・target の組で、違反（C0 を1件、C3 を1件）を (a) source のみ、(b) target のみ、(c) 両方、に置いて `prepare_readonly_workspace` を呼ぶ | 3通りとも P8 の識別子を持つ構造化エラー。(c) では detail から source 側・target 側それぞれの分類と件数を読み取れる |
| IT-TC-655-IS-02-2 | IS-02 | IS-02-1 (c) の構成で `issue_start.readonly_workspace.main` を引数つきで呼び、stderr と戻り値を取る | 戻り値が0以外。stderr に P8 があり `Traceback` が無い |
| IT-TC-655-IS-03-1 | IS-03 | 既存テストと同じ fixer 解放済み台帳と receipt を用意し、作業面に C0・C6 を各1件置いて `validate_pr_rereview` を呼ぶ | 識別子 `ISSUE_START_PR_REREVIEW_INVALID`。detail に C0・C6 の識別子と各件数1 |
| IT-TC-655-IS-04-1 | IS-04 | IS-01-1 の構成を native hook 経路（`hook_protocol` を通る gate の入口）に与え、hook の stdout を JSON として読む | JSON として読める。deny 理由に `ISSUE_START_PHASE_BINDING_INVALID` と C0・C3・C6 の識別子・件数がすべて入る |
