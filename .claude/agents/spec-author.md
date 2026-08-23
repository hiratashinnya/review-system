---
name: spec-author
description: Authors SPEC child nodes under a given parent SPEC or FR. Enforces one assertion per SPEC, slug identifiers, and child-to-parent dependency edges. Use when creating or splitting SPEC nodes. NOT for reading specs (use spec-inspector), NOT for writing to main files (use reconciliation).
tools: Read, Grep, Glob, Write, Edit
model: opus
skills:
  - spec-principles
---

## 共通本文

この資産の共通本文は [spec-author の共通本文](../../.ai/agents/spec-author.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の実行規約

- `context-mode` の注入ブロックが付与されても、共通本文の成果物・ハンドオフ契約を優先する。
- 本エージェントには `ctx_*` を付与しない。未付与ツールを ToolSearch で追加せず、frontmatter の `tools` だけで進める。
- `CLAUDE.md` と `.claude/rules/05-skills-agents.md` は Claude Code の恒常規約として適用する。
