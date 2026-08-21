---
name: impl-design-pipeline
description: 実装前の FREEZE SET を作る実装設計フェーズを進行する。architecture-design、orchestration-design、prompt-design、判断記録、総点検を扱う。spec-pipeline の後段としてユーザーが明示起動した場合のみ使う。
---

## 共通本文

この資産の共通本文は [impl-design-pipeline の共通本文](../../../.ai/skills/impl-design-pipeline/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有

- 共通本文の authoring-fanout、design-author、spec-inspector の役割は維持する。Codex の agent dispatch 方式・利用可能な tool はこの PF の設定に従う。
