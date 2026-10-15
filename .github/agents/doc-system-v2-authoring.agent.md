---
name: doc-system-v2-authoring
description: 'Shared doc-system v2 authoring contract common to every `*-author` agent (requirements-author, spec-author, analysis-author, design-author, verification-author): output shape (1 node = `{slug}.md` body + `{slug}.yaml` sidecar pair), slug/id assignment, sidecar key schema, unnamed edge notation, tmp mirror layout, and the scheduled self-judgment prohibition. Type-specific PREFIX/required-edges/body-format rules stay with each `*-author` agent — this file covers only the shared part. NOT an invocable task agent by itself; it is a shared reference doc linked from the author agents.'
disable-model-invocation: true
user-invocable: false
tools:
  - read_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [doc-system-v2-authoring の共通本文](../../.ai/agents/doc-system-v2-authoring.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: doc-system-v2-authoring -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-doc-system-v2-authoring を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
