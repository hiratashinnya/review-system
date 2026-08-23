---
name: doc-system-config-operator
description: Supports explanation, inspection, and changes to doc-system-v2/config.yml and its related CFG/SCM/SPEC/PROMPT design assets. Does not handle review_system-side config expansion.
tools: Read, Grep, Glob, Write, Edit, Bash
model: sonnet
skills:
  - spec-principles
---

## 共通本文

この資産の共通本文は [doc-system-config-operator の共通本文](../../.ai/agents/doc-system-config-operator.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の実行契約

- frontmatter の `tools`・`model`・`skills` はClaude Codeのloader/dispatch metadataとしてこのwrapperに残す。
- `context-mode`、`.claude/rules/`、`CLAUDE.md`、hookの実行制約はPF側の境界として適用し、共通本文へ持ち込まない。
