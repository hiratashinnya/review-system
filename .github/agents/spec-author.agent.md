---
name: spec-author
description: "Authors SPEC child nodes under a given parent SPEC or FR. Enforces 1-assertion-per-SPEC splitting and -N hierarchy numbering. Use when creating or splitting SPEC nodes. NOT for reading specs (use spec-inspector), NOT for writing to main files (use reconciliation)."
model: claude-opus-4-8
tools:
  - read_file
  - create_file
  - replace_string_in_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [spec-author の共通本文](../../.ai/agents/spec-author.md) にあります。必ず読み、その指示に従ってください。
