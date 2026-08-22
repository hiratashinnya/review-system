---
name: test-strategy
description: 本プロジェクト review-system のテスト戦略。公開関数ごとの unittest、TD/TC/TR の 3 点セット、commit-before-test、Codex CLI e2e の同形式を扱う。実装のテスト方法を計画する時に使い、仕様/設計や資産監査には使わない。
---

## 共通本文

この資産の共通本文は [test-strategy の共通本文](../../../.ai/skills/test-strategy/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有

- e2e は Codex CLI の利用可能な実行手段で `io/cli` を stdout 駆動で実行する。
- `.codex/hooks/agent-command-gate.sh` の対象ロールでは `|` や `2>` を含むログ保存コマンドを使わず、`python3 -m unittest discover -s tests/unit` を単体で実行する。ログが必要な場合は利用可能なファイル書き込み手段で保存する。
