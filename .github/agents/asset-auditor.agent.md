---
description: 'Read-only reuse auditor for new skills/agents/code. Before creating any new asset, inventories existing assets and reports overlap / contradiction / conflict plus a new-vs-extend recommendation. NOT for spec/requirement coverage checks — use spec-inspector for those.'
disable-model-invocation: true
user-invocable: false
tools:
  - read_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [asset-auditor の共通本文](../../.ai/agents/asset-auditor.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: asset-auditor -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-asset-auditor を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
