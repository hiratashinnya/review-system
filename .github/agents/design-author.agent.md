---
name: design-author
description: "Authors design-layer nodes: ORC, DS, MOD, DM, PORT, PRS, SCM, CFG, PROMPT. For TERM (analysis-placed, created by analysis-author) this agent appends only the design facet (Python type / defining module) when DM is settled — it does not create TERM nodes. Use when creating implementation-design nodes. NOT for requirements or analysis layer (use requirements-author or analysis-author), NOT for writing to main files (use reconciliation)."
disable-model-invocation: true
user-invocable: false
tools:
  - read_file
  - create_file
  - replace_string_in_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [design-author の共通本文](../../.ai/agents/design-author.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: design-author -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-design-author を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
