---
name: coverage-html
description: Generate a coverage HTML report for this project using unittest discover. Runs all tests under tests/, writes htmlcov/index.html, and prints a per-module summary (does NOT auto-install coverage; if it is missing, stop and escalate to the owner). Use when you want to see which lines are covered or uncovered.
---

## 共通本文

この資産の共通本文は [coverage-html の共通本文](../../../.ai/skills/coverage-html/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有

- 生成後、`SendUserFile` で `htmlcov/index.html` をユーザーへ送る。
- `issue-implementer` / `pr-reviewer` では agent-command-gate により `coverage run` が拒否されるため、カバレッジ計測は主文脈で行う。両ロールのテスト確認は `python3 -m unittest discover -s tests/unit` を単体で実行する。
