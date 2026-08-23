---
name: gh-create-issue
description: GitHub Issue の draft または作成を依頼された時に、重複確認、本文作成、ラベル分類、Project fields・親子関係・依存関係の設定、作成後検証を安全に行う。作成の明示依頼がある場合だけ実作成し、draft 依頼では提示に限定する。
---

## 共通本文

この資産の共通本文は [gh-create-issue の共通本文](../../../.ai/skills/gh-create-issue/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有

- GitHub 操作は connector-first とし、利用可能な GitHub connector/tool を先に使い、不足する機能だけ `gh` CLI で補う。
- Issue 本文の冒頭 attribution は `Codex AI agent が起票しました。` とする。
