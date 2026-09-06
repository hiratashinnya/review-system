---
name: gh-create-issue
description: GitHub Issue の draft または作成を依頼された時に、重複確認、本文作成、ラベル分類、Project fields・親子関係・依存関係の設定、作成後検証を安全に行う。作成の明示依頼がある場合だけ実作成し、draft 依頼では提示に限定する。
---

## 共通本文

この資産の共通本文は [gh-create-issue の共通本文](../../../.ai/skills/gh-create-issue/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有

- repository の `CLAUDE.md` と、そこから参照される規約を先に読む。共通本文の「適用規約」は Claude Code ではこれらを指す。
- Issue 本文の冒頭 attribution は `Claude Code (AI) が起票しました。` とする。
- owner の確認・承認が必要な場面では `AskUserQuestion` を使う。確認できない場合は共通本文どおり write 前に fail-close する。
- Claude Code on the web で GitHub Projects 系の MCP tool と `gh` CLI を利用できない場合は、共通本文 §5 の「Project へ書き込めない実行環境での代替」を適用する。
