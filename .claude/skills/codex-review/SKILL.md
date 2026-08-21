---
name: codex-review
description: ユーザーが明示起動する「Codex 公式 CLI (`codex exec`) への第二意見レビュー委譲」の入口。別モデルファミリ(OpenAI)に敵対的/セキュリティレビューを回す標準手順と、cybersecurity フィルタで最終応答が消えるハマりどころ＋rollout フォールバックを規約化する。agy MCP bridge (`mcp__agy__codex_*`) は使わない（→そちらは agy-delegate＝Gemini 用）。in-repo の Claude レビュー→merge は pr-reviewer。
disable-model-invocation: true
---

## 共通本文

この資産の共通本文は [codex-review の共通本文](../../../.ai/skills/codex-review/SKILL.md) にあります。必ず読み、その指示に従ってください。
