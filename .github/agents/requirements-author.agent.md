---
name: requirements-author
description: "Authors VAL, SR, FR, and NFR nodes under a given parent. Use when creating requirements-layer nodes. NOT for SPEC nodes (use spec-author), NOT for writing to main files (use reconciliation)."
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

この資産の共通本文は [requirements-author の共通本文](../../.ai/agents/requirements-author.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: requirements-author -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-requirements-author を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
