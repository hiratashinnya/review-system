---
name: native-stacked-pr
description: Create, register, verify, and maintain GitHub native stacked PRs for dependent work. Use for dependent PRs, existing PR chains, or gh stack operations. Preserve the repo's gitgate branch-source checks, protect existing lower PRs, verify remote stack metadata, and leave merging to the owner.
---

## 共通本文

この資産の共通本文は [native-stacked-pr の共通本文](../../../.ai/skills/native-stacked-pr/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Copilot 固有

- `.github/skills/` の能力 Skill として起動する。Prompt／Agent／Instructions と取り違えない。
- 利用可能な GitHub read 手段を優先し、不足する native stack 機能を公式 CLI または UI で補う。機能が使えないときは未登録と報告する。
- 実行機構に置き換えても分岐元ゲート・下段保護・native 登録証明・owner 手動 merge の境界を維持する。
