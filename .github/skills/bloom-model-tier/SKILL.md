---
name: bloom-model-tier
description: Choose a GitHub Copilot model ID for a custom agent by classifying its dominant Bloom's-revised cognitive level AND whether its difficulty is thoroughness-bound or judgment-bound. Use when deciding the Copilot `model:` setting for an agent. NOT runtime control-flow (orchestration-design), NOT prompt template design (prompt-design).
---

## 共通本文

この資産の共通本文は [bloom-model-tier の共通本文](../../../.ai/skills/bloom-model-tier/SKILL.md) にあります。必ず読み、その指示に従ってください。

## GitHub Copilot 固有の写像

Copilot の agent frontmatter は `model:` に Copilot が利用可能なモデル ID を指定する。PF 中立の「中位モデル層」「最上位モデル層」は、このリポジトリで使用している Copilot のモデル ID ではそれぞれ `claude-sonnet-5`、`claude-opus-4-8` に対応する。共通の推論予算は Copilot の agent frontmatter では表現できず、モデルIDだけを写像する。低位モデル層は live の利用可能 ID を確認できた場合だけ指定する。確認できない場合は架空の model ID を追加せず STOP し、利用可能 ID と採用可否をオーナーへ確認する。Claude Code の `haiku`/`sonnet`/`opus` や `effort:`、Codex の `model_reasoning_effort` を Copilot frontmatter にそのまま持ち込まない。

```yaml
model: claude-sonnet-5 # PF 中立の中位モデル層
```
```yaml
model: claude-opus-4-8 # PF 中立の最上位モデル層
```
