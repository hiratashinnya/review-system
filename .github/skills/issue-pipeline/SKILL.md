---
name: issue-pipeline
description: Orchestrate GitHub Issues through investigation, verification design, solution planning, Red tests, implementation and independent phase reviews. AI roles do not merge; the owner reviews the blocker report and merges manually.
---

## 共通本文

この資産の共通本文は [issue-pipeline の共通本文](../../../.ai/skills/issue-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Copilot 固有

- この PF には `issue-investigator` / `ac-designer` / `change-planner` / `plan-reviewer` / `test-writer` / `adviser` / `issue-implementer` / `issue-fixer` / `pr-reviewer` の専用 Agent は移植されていない。利用可能な Copilot の実行手段へ置き換えるが、共通本文の役割分担・順序・owner decision・STOP 契約は維持する。
- Skill は `.github/skills/`、Prompt は `.github/prompts/`、Agent は `.github/agents/`、常時 Instructions は `.github/copilot-instructions.md` の起動方式を使う。それらを取り違えず、Instructions ファイルをこの wrapper の本文として複製しない。

- 全Issueの1a検証設計→単独レビュー→1b解決設計→整合レビュー→owner承認→2aテスト設計→単独レビュー→2b実装の順序を維持する。PFの等価な権限制限を確認できない実行先へdispatchしない。
