---
name: bloom-model-tier
description: カスタム agent の主な認知負荷を Bloom 改訂版で分類し、Codex CLI session/config の model と model_reasoning_effort を決める。custom agent の実行設定を決める時に使い、実行制御やプロンプトテンプレート設計には使わない。
---

## 共通本文

この資産の共通本文は [bloom-model-tier の共通本文](../../../.ai/skills/bloom-model-tier/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有の写像

PF 中立のモデル層と推論予算は、Codex CLI の session/config へ独立に写像する。この写像の適用先は Codex CLI の session/config である。`.codex/agents/*.toml` は session の任意設定を継承するため、各 custom-agent TOML へ `model` や `model_reasoning_effort` を複製しない。12セルのモデル層差分と中立予算を欠落させない。

| PF 中立のモデル層 | Codex CLI session/config の `model` |
|---|---|
| 低位モデル層 | `model: gpt-5.6-luna` |
| 中位モデル層 | `model: gpt-5.6-luna` |
| 最上位モデル層 | `model: gpt-5.6-sol` |

| PF 中立の予算 | Codex CLI session/config の `model_reasoning_effort` |
|---|---|
| 最小 | `low` |
| 小 | `medium` |
| 中 | `high` |
| 大 | `xhigh` |
| 最大 | `max` |

Codex CLI session/config 用の設定例：

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "high" # Bloom Lv5 評価・判断ボトルネック
```
