---
name: issue-pipeline
description: Orchestrate GitHub Issues through investigation, verification design, solution planning, Red tests, implementation and independent phase reviews. AI roles do not merge; the owner reviews the blocker report and merges manually.
---

## 共通本文

この資産の共通本文は [issue-pipeline の共通本文](../../../.ai/skills/issue-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Copilot 固有

- この PF には `issue-investigator` / `ac-designer` / `change-planner` / `plan-reviewer` / `test-writer` / `adviser` / `issue-implementer` / `issue-fixer` / `pr-reviewer` の専用 Agent は移植されていない。
- 実行先へ委譲する場合、PF で等価な権限制限を確認できない実行先へ dispatch しない。
- Skill は `.github/skills/`、Prompt は `.github/prompts/`、Agent は `.github/agents/`、常時 Instructions は `.github/copilot-instructions.md` から読み込む。それらを取り違えず、Instructions の本文をこの wrapper に複製しない。
