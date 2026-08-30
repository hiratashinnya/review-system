---
name: test-strategy
description: Test strategy for THIS project (review-system) — unittest per public function, TD (Markdown test design) + TC (Python unittest code) + TR (test result with result/log_ref frontmatter), commit-before-test, same 3-set for Claude Code e2e. Use when planning HOW to test the implementation. NOT spec/design (see domain-model/schema-design), NOT asset auditing (see asset-auditor).
status: tailored — derived from .claude/standards/test-strategy
---

## 共通本文

この資産の共通本文は [test-strategy の共通本文](../../../.ai/skills/test-strategy/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有

- e2e は Claude Code エージェントで `io/cli` を stdout 駆動で実行する。
- `issue-implementer` / `pr-reviewer` では agent-command-gate のため `|` や `2>` を含むログ保存コマンドを使わず、`python3 -m unittest discover -s tests/unit` を単体で実行する。ログが必要な場合は利用可能なファイル書き込み手段で保存する。
- context-mode の実行系ツール、hook、許可ツールはClaude Codeの設定に従う。
