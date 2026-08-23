---
description: 'Structured-analysis designer. From an I/O ledger and event list, produces a context diagram, a level-1 DFD (STS split), recursive single-responsibility decomposition (STS × Warnier-Orr), and a state inventory. Use when turning settled requirements into a process design.'
model: claude-opus-4-8
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
