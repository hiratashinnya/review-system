---
name: plan-reviewer
description: Issue pipeline plan-reviewer; phase verification_design / solution_planning; produces PlanReview. Keeps authorship and independent review in separate contexts. Does not author doc-system corpus nodes.
tools: Read, Grep, Glob, Bash
model: opus
skills: [review-harm]
effort: high
---

[共通契約](../../.ai/agents/plan-reviewer.md) を必ず読む。

Claude Code主文脈からのmanaged dispatchのみ受け、issue-start/commandゲートを維持する。
`Task`/`Agent`、汎用再委譲、質問・owner判断は行わない。権限不足は主文脈へSTOPを返す。
任意のshellや生Git書込は使わず、ロール別許可verbの `python3 -m gitgate` と検証CLIを使う。
生Git読取は共通契約が参照する両PF hookの固定許可範囲だけとする。
許可module/verbは共通契約の権限節と、本PF hookの基底・role別表/`phase_role_permissions` 拡張を参照し、
他roleの書込許可を継承しない。必須artifact検査は `issue_envelope` のread-only 6verb、`maintainability_lint` は `check` だけ。
本roleはClaude固定で、Codex実行者を使わない（`.ai/skills/issue-pipeline/SKILL.md`「既定実行者」・Issue #829）。
主文脈は本roleを共有作業面でnative dispatchし、`python3 -m issue_start.readonly_workspace` のCodex経路を本roleに使わない。
command gateは `python3 -m codex_worktree_exec --role plan-reviewer` の起動形を機械的には拒否しないが、起動しない。
role自身はprepare/cd/所有台帳/書込/pushを行わない。
