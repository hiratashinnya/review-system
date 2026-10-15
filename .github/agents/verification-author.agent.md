---
name: verification-author
description: "Authors verification-layer nodes: TD, TC, TR, VERIFY, FND, DD, Q, PEND. Use when creating test designs, test cases, test results, findings, or decision records. NOT for SPEC nodes (use spec-author), NOT for writing to main files (use reconciliation)."
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

この資産の共通本文は [verification-author の共通本文](../../.ai/agents/verification-author.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: verification-author -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-verification-author を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
