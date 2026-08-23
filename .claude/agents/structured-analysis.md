---
name: structured-analysis
description: Structured-analysis designer. From an I/O ledger and event list, produces a context diagram, a level-1 DFD (STS split), recursive single-responsibility decomposition (STS × Warnier-Orr), and a state inventory. Use when turning settled requirements into a process design.
tools: Read, Grep, Glob, Write, Edit
model: opus
skills:
  - spec-principles
---

## 共通本文

この資産の共通本文は [structured-analysis の共通本文](../../.ai/agents/structured-analysis.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の実行規約

- `context-mode` の注入ブロックが付与されても、共通本文の成果物・ハンドオフ契約を優先する。
- 本エージェントには `ctx_*` を付与しない。未付与ツールを ToolSearch で追加せず、frontmatter の `tools` だけで進める。
- `CLAUDE.md` と `.claude/rules/05-skills-agents.md` は Claude Code の恒常規約として適用する。
