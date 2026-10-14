---
description: 'Read-only inspector for specs/requirements AND implementation-design docs. Cross-checks an I/O ledger, event list, process/DFD, schema, and the design freeze set (module/interface/protocol/persistence/orchestration/prompt/logging) for coverage gaps (orphan outputs, unused inputs, undefined-reaction events, DFD-process→module gaps), I/O splitting violations, ledger-number mismatches, and contradictions. Returns a numbered gap list (G#) and flags contradictions for confirmation instead of resolving them. Use proactively after editing requirements, ledgers, event lists, or design docs (e.g. as the impl-design-pipeline total-check).'
disable-model-invocation: true
user-invocable: false
tools:
  - read_file
  - grep_search
  - file_search
---

## 共通本文

この資産の共通本文は [spec-inspector の共通本文](../../.ai/agents/spec-inspector.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: spec-inspector -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-spec-inspector を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
