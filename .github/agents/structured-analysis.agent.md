---
description: 'Structured-analysis designer. From an I/O ledger and event list, produces a context diagram, a level-1 DFD (STS split), recursive single-responsibility decomposition (STS × Warnier-Orr), and a state inventory. Use when turning settled requirements into a process design.'
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

この資産の共通本文は [structured-analysis の共通本文](../../.ai/agents/structured-analysis.md) にあります。必ず読み、その指示に従ってください。

## GitHub Copilot 固有の実行上の注意

GitHub 上で Mermaid を描画する場合は、共通本文の記法に加えてラベル内の丸括弧を避け、リンクを矢印で表す。

<!-- model-policy: .ai/model-policy.json; agent: structured-analysis -->

このファイルは停止状態の template です。[モデル準備手順](../../model_policy/README.md) に従い、同一 surface の一覧から runtime-structured-analysis を生成し、解決済みモデルを確認してから起動してください。default model の継承による起動は禁止します。
