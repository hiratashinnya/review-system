---
name: analysis-author
description: "Authors ACTOR, I, O, D, P, E, and TERM (analysis facet = ubiquitous-language term definition) nodes for the analysis layer. Use when creating context/DFD-layer nodes. NOT for FR/SPEC/NFR (use requirements-author or spec-author), NOT for writing to main files (use reconciliation). TERM's design facet (Python type / defining module) is appended by design-author when DM is settled."
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

この資産の共通本文は [analysis-author の共通本文](../../.ai/agents/analysis-author.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: analysis-author -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-analysis-author を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
