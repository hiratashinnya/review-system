---
name: doc-system-config-operator
description: 'Supports explanation, inspection, and changes to doc-system-v2/config.yml and related CFG/SCM/SPEC/PROMPT design assets. Does not handle review_system-side config expansion.'
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

この資産の共通本文は [doc-system-config-operator の共通本文](../../.ai/agents/doc-system-config-operator.md) にあります。必ず読み、その指示に従ってください。
