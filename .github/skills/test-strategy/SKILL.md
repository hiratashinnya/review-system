---
name: test-strategy
description: Test strategy for THIS project (review-system) — unittest per public function, TD (Markdown test design) + TC (Python unittest code) + TR (test result with result/log_ref frontmatter), commit-before-test, same 3-set for end-to-end. Use when planning HOW to test the implementation. NOT spec/design, NOT asset auditing.
---

## 共通本文

この資産の共通本文は [test-strategy の共通本文](../../../.ai/skills/test-strategy/SKILL.md) にあります。必ず読み、その指示に従ってください。

## GitHub Copilot 固有

- e2e は Copilot で利用可能な Agent または Prompt の起動方式に合わせて `io/cli` を実行する。共通本文のTD/TC/TR/ログの対応は維持する。
