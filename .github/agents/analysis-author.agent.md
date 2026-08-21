---
name: analysis-author
description: "Authors ACTOR, I, O, D, P, E, and TERM (analysis facet = ubiquitous-language term definition) nodes for the analysis layer. Use when creating context/DFD-layer nodes. NOT for FR/SPEC/NFR (use requirements-author or spec-author), NOT for writing to main files (use reconciliation). TERM's design facet (Python type / defining module) is appended by design-author when DM is settled."
model: claude-sonnet-5
tools:
  - read_file
  - create_file
  - replace_string_in_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [analysis-author の共通本文](../../.ai/agents/analysis-author.md) にあります。必ず読み、その指示に従ってください。
