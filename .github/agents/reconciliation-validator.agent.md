---
name: reconciliation-validator
description: 'Read-only structural validator for authored nodes in tmp/<sprint>/ before write-back. Checks ID existence, ref_version match, edge notation, SPEC/TD/TR type rules and FND edge-reversal; returns VALIDATION_OK (with a self-fixable flag list) or ROLLBACK. NEVER writes any file. NOT for committed spec/design coverage gaps (use spec-inspector), NOT the writer that commits nodes to main files (use reconciliation).'
model: claude-sonnet-5
tools:
  - read_file
  - grep_search
  - file_search
  - run_in_terminal
---

## 共通本文

この資産の共通本文は [reconciliation-validator の共通本文](../../.ai/agents/reconciliation-validator.md) にあります。必ず読み、その指示に従ってください。
