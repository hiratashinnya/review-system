---
name: issue-pipeline
description: Orchestrate a batch of open GitHub Issues through implement→PR→review→merge→close, one Issue at a time. The main thread stays thin — it triages processing order, dispatches issue-implementer / pr-reviewer sub-agents (model tier via bloom-model-tier, risk-based reviewer model), exchanges decisions with the owner via AskUserQuestion (showing premises/tradeoffs first), and tracks progress. Use when issue handling should proceed end-to-end with governance. NOT for authoring doc-system-v2 nodes (use spec-pipeline / impl-design-pipeline).
---

> **共通本文（必読）**: [`.ai/skills/issue-pipeline/SKILL.md`](../../../.ai/skills/issue-pipeline/SKILL.md)。実行前に必ず読み、Claude Code 固有の起動・権限・hook 制約を追加適用する。

設計判断の根拠は [issue-pipeline の canonical rationale](../../../.ai/rationale/issue-pipeline.md) を参照してください。

## Claude Code 固有の dispatch 契約

- 主文脈だけが `AskUserQuestion` を使い、順序・オーナー判断・先送り・スコープ拡張を担う。`issue-implementer`、`issue-fixer`、`pr-reviewer` は非対話で STOP 報告する。
- `issue-implementer` の Task/Agent dispatch は `ISSUE_START_BINDING_V1` marker をちょうど1つ含み、`isolation: "worktree"` をパラメータで渡す。marker の repository、issue、branch、base_ref、base_oid、base_pr は後続の branch 作成値と一致させる。
- `.claude/hooks/issue-start-gate.sh`、`agent-command-gate.sh`、worktree／karte の hook が有効な managed path を使い、契約エラーは迂回せず fail-close する。
- 実装は `issue-implementer`、レビュー／マージは `pr-reviewer`、レビュー是正は `issue-fixer` に分ける。実装者は merge 不可、レビュー者は push 不可の機械ゲートを前提にする。
- Claude 固有の rationale は `.claude/rationale/issue-pipeline.md` を参照するが、共有契約の正本は上記 `.ai` 本文である。
- `.claude/agents/*.md` の変更内容が同一セッションの dispatch に直ちに反映されるとは限らない。変更後の契約を前提にせず、各 dispatch の実際の STOP 理由・受理形状を観測して適用契約を確認する。
