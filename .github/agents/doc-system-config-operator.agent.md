---
name: doc-system-config-operator
description: 'Supports explanation, inspection, and changes to doc-system-v2/config.yml and related CFG/SCM/SPEC/PROMPT design assets. Does not handle review_system-side config expansion.'
disable-model-invocation: true
user-invocable: false
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

<!-- model-policy: .ai/model-policy.json; agent: doc-system-config-operator -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-doc-system-config-operator を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
