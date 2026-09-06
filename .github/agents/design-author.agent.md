---
name: design-author
description: "Authors design-layer nodes: ORC, DS, MOD, DM, PORT, PRS, SCM, CFG, PROMPT. For TERM (analysis-placed, created by analysis-author) this agent appends only the design facet (Python type / defining module) when DM is settled — it does not create TERM nodes. Use when creating implementation-design nodes. NOT for requirements or analysis layer (use requirements-author or analysis-author), NOT for writing to main files (use reconciliation)."
model: claude-opus-4-8
tools:
  - read_file
  - create_file
  - replace_string_in_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [design-author の共通本文](../../.ai/agents/design-author.md) にあります。必ず読み、その指示に従ってください。
