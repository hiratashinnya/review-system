---
name: impl-design-pipeline
description: Orchestrate the implementation-design phase into a pre-implementation FREEZE SET — architecture-design → orchestration-design → prompt-design, recording design decisions (DD#) and running a spec-inspector total-check. Run only when explicitly invoked (the spec → impl-design bridge). Downstream of spec-pipeline.
disable-model-invocation: true
---

## 共通本文

この資産の共通本文は [impl-design-pipeline の共通本文](../../../.ai/skills/impl-design-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有

- `disable-model-invocation: true` の明示起動スキルとして扱う。
- 対話が必要な矛盾停止・DD# の暫定決定は主文脈に残す。非対話のノード著作は利用可能な authoring-fanout／design-author へ委譲する。
