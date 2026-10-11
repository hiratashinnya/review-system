---
name: native-stacked-pr
description: GitHub ネイティブ stacked PR を作成・登録・検証・追随する repo 運用能力。依存 PR の上で先行着手するとき、既存 PR を native stack にするとき、gh stack や stacked PR の運用時に使う。fresh exact OID の gitgate 分岐、既存下段の保護、remote stack metadata 検証、owner 手動 merge を守る。
---

## 共通本文

この資産の共通本文は [native-stacked-pr の共通本文](../../../.ai/skills/native-stacked-pr/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有

- repository の `CLAUDE.md` と適用される `.claude/rules/*.md` を先に読み、ロール別 command gate と `gitgate` 契約を守る。
- `Bash` では TUI を避け、明示 target と `gh stack view --json` を使う。公式 Skill の merge 操作例は本 repo では実行しない。
- 実装とレビューを別コンテキストへ分離する。supervisor を要求せず、利用者が指定した通常 subagent の経路を保つ。
