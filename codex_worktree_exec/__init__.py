"""Claude の issue-implementer / issue-fixer が自分の linked worktree で Codex に編集とテストだけを行わせる薄いラッパー。

`.claude/hooks/agent-command-gate.sh` が `codex_worktree_exec.roles` を import するため、
ここでは何も import しない（ゲートの判定経路に無関係な依存を持ち込まない）。
契約は `docs/methods/codex-workspace-binding.md` を正とする（Issue #538 PR-B）。
"""
