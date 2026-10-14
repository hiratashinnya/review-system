---
name: bloom-model-tier
description: カスタム agent の主な認知負荷を Bloom 改訂版で分類し、Codex CLI session/config の model と model_reasoning_effort を決める。custom agent の実行設定を決める時に使い、実行制御やプロンプトテンプレート設計には使わない。
---

## 共通本文

この資産の共通本文は [bloom-model-tier の共通本文](../../../.ai/skills/bloom-model-tier/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有の写像

系統・層・予算の正本は [.ai/model-policy.json](../../../.ai/model-policy.json) の `platforms.codex` である。Bloom の低位／中位／最上位はそれぞれ `low`／`mid`／`top` を参照する。具体 ID の一覧を wrapper に複製しない。

[解決手順](../../../model_policy/README.md) に従って `python3 -m model_policy resolve` を実行し、`resolved` の対象層を Codex CLI session/config の `model` へ指定する。`model_reasoning_effort` は同じ正本の `budgets` から独立に選ぶ。12セルのモデル層差分と中立予算を欠落させない。

`.codex/agents/*.toml` は session 設定を継承するため `model` や `model_reasoning_effort` を複製しない。取得失敗・合致なし・曖昧な最新は STOP し、別 major や低い層へ代替しない。解決結果と実際の session model が一致してから実行する。
