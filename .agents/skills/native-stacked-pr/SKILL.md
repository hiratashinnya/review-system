---
name: native-stacked-pr
description: GitHub ネイティブ stacked PR を作成・登録・検証・追随する repo 運用能力。依存 PR の上で先行着手するとき、既存 PR を native stack にするとき、gh stack や stacked PR の運用時に使う。fresh exact OID の gitgate 分岐、既存下段の保護、remote stack metadata 検証、owner 手動 merge を守る。
---

## 共通本文

この資産の共通本文は [native-stacked-pr の共通本文](../../../.ai/skills/native-stacked-pr/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex 固有

- GitHub metadata の読取は connector-first とし、不足する stack 機能だけ公式 `gh stack`／`gh api` で補う。
- shell は非対話で実行する。`gh stack view --json`、明示 target を用い、TUI や裸の `submit`／`modify` を起動しない。
- 実装とレビューは別 subagent へ委譲する。owner 判断を要する場合は具体的成果物・推奨・影響を呼び出し元へ返す。
