---
description: 'Non-interactive orchestrator that fans out a BATCH of independent authoring targets to the per-type *-author agent selected by an `author` parameter (requirements-author | spec-author | analysis-author | design-author | verification-author), then runs reconciliation-validator once over the batch and hands VALIDATION_OK to reconciliation for write-back. Use ONLY when a pipeline has produced a list of multiple independent parent nodes each needing the same layer of authoring. NOT for a single-node author task. NOT a validator, NOT the writer to main files. Cannot ask the user — on any ROLLBACK, contradiction, or ambiguity it STOPs and reports to its caller.'
disable-model-invocation: true
user-invocable: false
tools:
  - read_file
  - grep_search
  - file_search
  - run_in_terminal
---

> **Copilot 固有の委譲注記**：Claude Code の `Task` に相当する標準ツールがない環境では、共通本文の委譲手順を chat participant / hand-off 等の利用可能な agent-invocation 機能へ読み替えてください。読み替え先がない場合は、呼び出し元ワークフローへ手順と STOP 条件を返します。

## 共通本文

この資産の共通本文は [authoring-fanout の共通本文](../../.ai/agents/authoring-fanout.md) にあります。必ず読み、その指示に従ってください。

<!-- model-policy: .ai/model-policy.json; agent: authoring-fanout -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-authoring-fanout を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
