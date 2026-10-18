# IT-TD-655 issue_start — 検査を呼ぶ経路の集約診断と識別子の結合テスト設計

- 作成：ac-designer（Claude Code (AI)）／VD 葉：`issue_start/verification_design/VD-655.toml`（ID `VD-655-issue-start`）
- 対象境界：`phase_dispatch`・`readonly_workspace`・`pr_rereview` ↔ `codex_worktree_exec.source_snapshot`（集約した拒否）↔ `gate_support.IssueStartError` ↔ `hook_protocol`（deny 理由）
- 記号 C0〜C8・P1〜P8 は [ST-TD-655](../../../codex_worktree_exec/verify/designs/ST-TD-655.md) §2・§3 の定義。TC は [IT-TC-655](IT-TC-655.md)。
- 「上位」欄は、対応する ST-TD（ST-TD 側の見出しに Issue AC がある）と、根拠の契約条項（snapshot `128a32b` の path:行）を示す。

### IT-TD-655-IS-01 phase_dispatch
- 上位：ST-TD-655-12（1）・ST-TD-655-03／Issue AC12・AC3／`docs/methods/codex-workspace-binding.md:296`（native/Codex の全工程入力検査で拒否）
- 1b依存：P7
- 合格条件：未追跡違反（C0・C3・C6）がある作業面への工程 dispatch で、`IssueStartError` の識別子が `ISSUE_START_PHASE_BINDING_INVALID`、detail に全分類の識別子と件数が入る。検査は1回の呼出しで全分類を返す。

### IT-TD-655-IS-02 readonly_workspace の準備
- 上位：ST-TD-655-12（1・2）／Issue AC12・Scope 3（F-655-03）／`docs/methods/codex-workspace-binding.md:276-278`（source で検査し、両面の未追跡集合も検査する）
- 1b依存：P4・P8
- 合格条件：
  1. 違反を source 側だけ、target 側だけ、両方に置いた3通りで、準備の失敗は P8 の識別子を持つ構造化エラーになる（素の `ValueError` のまま外へ出ない）。
  2. 両方に置いた場合、1回の失敗の detail に source 側と target 側の両方の分類・件数が、どちらの作業面かを区別できる形で入る。
  3. `main` から呼んだとき、終了コードは0以外で、stderr に `Traceback` が無い。

### IT-TD-655-IS-03 pr_rereview
- 上位：ST-TD-655-12（1）／Issue AC12・Scope 3（`pr_rereview` を全経路に含める）／`docs/methods/codex-workspace-binding.md:296`・`323`（既存 PR の再レビューは専用契約を使う）
- 1b依存：P7
- 合格条件：fixer 解放済みの正当な再レビュー入力で作業面に違反を置くと、識別子が `ISSUE_START_PR_REREVIEW_INVALID`、detail に全分類の識別子と件数が入る。

### IT-TD-655-IS-04 hook の deny 理由
- 上位：ST-TD-655-12（1・4）／Issue AC12／`docs/tools/issue-start-and-branch-source.md:35`（deny は reason を PreToolUse response に含める）
- 1b依存：P4
- 合格条件：native の PreToolUse 経路（`hook_protocol`）で IS-01 の拒否が起きたとき、deny 理由に識別子と detail の全分類識別子・件数が切り詰められずに入る。hook の出力は JSON として読める。
