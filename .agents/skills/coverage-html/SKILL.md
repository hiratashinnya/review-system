---
name: coverage-html
description: このプロジェクトで実装またはテストコードを CLI で変更した時だけ、unittest discover と coverage.py でカバレッジを確認する。生成物は commit しない。
---

## 共通本文

この資産の共通本文は [coverage-html の共通本文](../../../.ai/skills/coverage-html/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有

- `.codex/hooks/agent-command-gate.sh` により、`issue-implementer` / `pr-reviewer` からの `coverage run` は拒否される。カバレッジ計測は主文脈で行い、両ロールのテスト確認は `python3 -m unittest discover -s tests/unit` を単体で実行する。
