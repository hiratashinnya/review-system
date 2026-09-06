---
name: analysis-author
description: "Authors ACTOR, I, O, D, P, E, and TERM (analysis facet = ubiquitous-language term definition) nodes for the analysis layer. Use when creating context/DFD-layer nodes. NOT for FR/SPEC/NFR (use requirements-author or spec-author), NOT for writing to main files (use reconciliation). TERM's design facet (Python type / defining module) is appended by design-author when DM is settled."
tools: Read, Grep, Glob, Write, Edit
model: sonnet
skills:
  - spec-principles
---

## 共通本文

この資産の共通本文は [analysis-author の共通本文](../../.ai/agents/analysis-author.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の実行契約

- frontmatter の `tools`・`model`・`skills` は Claude Code のloader/dispatch metadataであり、このwrapperに残す。
- `context-mode` の注入ブロックが付与された場合は、成果物をファイルへ出力し、ハンドオフのパスと1行要約を返す契約を優先する。
- 本wrapperの `tools` に `Task` や `ctx_*` は含まれない。未付与のツールを追加取得せず、frontmatterで許可された手段だけを使う。
- `.claude/rules/` と `CLAUDE.md` の常時適用規約、およびClaude Codeのhookによる実行制約はPF側の境界として適用する。
