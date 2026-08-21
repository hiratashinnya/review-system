---
name: impl-design-pipeline
description: Orchestrate the implementation-design phase into a pre-implementation FREEZE SET — architecture-design → orchestration-design → prompt-design, recording design decisions (DD#) and running a spec-inspector total-check. Run only when explicitly invoked (the spec → impl-design bridge). Downstream of spec-pipeline.
---

## 共通本文

この資産の共通本文は [impl-design-pipeline の共通本文](../../../.ai/skills/impl-design-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Copilot 固有

- Skill の起動は `.github/skills/` のこの wrapper を使う。Prompt（`.github/prompts/`）、Agent（`.github/agents/`）、常時 Instructions（`.github/copilot-instructions.md`）をこの Skill の代替として扱わない。
- 共通本文にない Copilot 固有の起動・ツール制約を必要とする場合だけ、この wrapper に追記する。
