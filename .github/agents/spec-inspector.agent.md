---
description: 'Read-only inspector for specs/requirements AND implementation-design docs. Cross-checks I/O ledger, event list, process/DFD, schema, and the design freeze set for coverage gaps, I/O splitting violations, ledger-number mismatches, and contradictions. Returns a numbered gap list (G#). Use proactively after editing requirements, ledgers, or design docs.'
model: claude-sonnet-5
tools:
  - read_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [spec-inspector の共通本文](../../.ai/agents/spec-inspector.md) にあります。必ず読み、その指示に従ってください。
