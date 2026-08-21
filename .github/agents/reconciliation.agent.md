---
name: reconciliation
description: 'Writes validated nodes from tmp/<sprint>/ to main files after reconciliation-validator passes. Applies the validator''s self_fix instructions, commits nodes to the doc-system-v2 corpus, then clears tmp. NOT for authoring new nodes (use *-author agents), NOT for structural validation (use reconciliation-validator), NOT for spec coverage inspection (use spec-inspector).'
model: claude-sonnet-5
tools:
  - read_file
  - grep_search
  - file_search
  - create_file
  - replace_string_in_file
  - run_in_terminal
---

## 共通本文

この資産の共通本文は [reconciliation の共通本文](../../.ai/agents/reconciliation.md) にあります。必ず読み、その指示に従ってください。
