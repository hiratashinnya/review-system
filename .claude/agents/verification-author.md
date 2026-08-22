---
name: verification-author
description: "Authors verification-layer nodes: TD, TC, TR, VERIFY, FND, DD, Q, PEND. Use when creating test designs, test cases, test results, findings, or decision records. NOT for SPEC nodes (use spec-author), NOT for writing to main files (use reconciliation)."
tools: Read, Grep, Glob, Write, Edit
model: opus
skills:
  - spec-principles
---

## 共通本文

この資産の共通本文は [verification-author の共通本文](../../.ai/agents/verification-author.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の実行規約

- `context-mode` の注入ブロックが付与されても、共通本文の成果物・ハンドオフ契約を優先する。
- 本エージェントには `ctx_*` を付与しない。未付与ツールを ToolSearch で追加せず、frontmatter の `tools` だけで進める。
- `CLAUDE.md` と `.claude/rules/05-skills-agents.md` は Claude Code の恒常規約として適用する。
