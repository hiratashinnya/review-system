---
name: dsv2-lookup
description: Retrieves and digests doc-system-v2 nodes to populate the caller's context efficiently. Given a topic/id/type hint, uses `python3 -m dsv2 index` to build meta.json (id/type/stage/status/title/version/labels/edges/body_path per node), filters candidates via grep/python over that JSON, then Reads only the matching body_path files. Uses `dsv2 deps`/`dependents` for edge traversal. Returns a compact digest (ids + versions + body_path + key excerpts + related edges) instead of dumping whole files. Use when the caller needs the relevant nodes loaded compactly before further work. NOT spec/design inspection (use spec-inspector), NOT reuse/overlap audit (use asset-auditor), NOT node authoring/editing (use the *-author / reconciliation agents).
tools: Bash, Read, Grep, Glob, mcp__plugin_context-mode_context-mode__ctx_search, mcp__plugin_context-mode_context-mode__ctx_index, mcp__plugin_context-mode_context-mode__ctx_batch_execute, mcp__plugin_context-mode_context-mode__ctx_execute
model: sonnet
---

## 共通本文

この資産の共通本文は [dsv2-lookup の共通本文](../../.ai/agents/dsv2-lookup.md) にあります。必ず読み、その指示に従ってください。
