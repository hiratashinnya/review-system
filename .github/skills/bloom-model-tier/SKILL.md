---
name: bloom-model-tier
description: Choose a GitHub Copilot model ID for a custom agent by classifying its dominant Bloom's-revised cognitive level AND whether its difficulty is thoroughness-bound or judgment-bound. Use when deciding the Copilot `model:` setting for an agent. NOT runtime control-flow (orchestration-design), NOT prompt template design (prompt-design).
---

## 共通本文

この資産の共通本文は [bloom-model-tier の共通本文](../../../.ai/skills/bloom-model-tier/SKILL.md) にあります。必ず読み、その指示に従ってください。

## GitHub Copilot 固有の写像

系統・層と各 agent の分類の正本は [.ai/model-policy.json](../../../.ai/model-policy.json) の `platforms.copilot`／`copilot_agents` である。中位／最上位は `mid`／`top` を参照する。低位は未定義のため STOP し、架空 ID や別層を追加しない。

共通の推論予算は Copilot の agent frontmatter では表現できず、モデルIDだけを写像する。Claude の `effort:` や Codex の `model_reasoning_effort` を持ち込まない。

追跡対象 agent は停止状態の template である。[準備手順](../../../model_policy/README.md) に従い SDK／IDE API／CLI の `/model` から同一 surface の一覧を取得し、`python3 -m model_policy prepare-copilot --surface <cli|ide> --catalog <一覧.json>` でローカル runtime agent を生成する。model 未指定の default 継承では起動しない。解決済み ID を実行前に確認し、合致なし・取得失敗・曖昧な最新は STOP する。
