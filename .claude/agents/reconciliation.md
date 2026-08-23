---
name: reconciliation
description: Writes validated nodes from tmp/<sprint>/ to main files after reconciliation-validator passes. Applies the validator's self_fix instructions, commits nodes to the doc-system-v2 corpus, then clears tmp. NOT for authoring new nodes (use *-author agents), NOT for structural validation (use reconciliation-validator), NOT for spec coverage inspection (use spec-inspector).
tools: Read, Grep, Glob, Write, Edit, Bash
model: sonnet
skills:
  - spec-principles
---

## 共通本文

この資産の共通本文は [reconciliation の共通本文](../../.ai/agents/reconciliation.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の反映経路

- `Read` / `Grep` / `Glob` で対象を確認し、tmp とコーパスの本文反映は `Write` / `Edit` に限定する。`Task` は本 wrapper に付与せず、著作・検証の委譲は呼び出し元の契約に従う。
- 決定論的な status 遷移、FND reverse、tmp 掃除だけは wrapper に許可された専用 Bash 操作を使う。`rm` などの代替削除は行わない。
- `../../.ai/agents/reconciliation.md` は Claude wrapper から共通契約へ到達する固定パスである。
