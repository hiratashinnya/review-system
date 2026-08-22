---
name: bloom-model-tier
description: カスタム agent の主な認知負荷を Bloom 改訂版で分類し、Codex CLI session/config の model と model_reasoning_effort を決める。custom agent の実行設定を決める時に使い、実行制御やプロンプトテンプレート設計には使わない。
---

## 共通本文

この資産の共通本文は [bloom-model-tier の共通本文](../../../.ai/skills/bloom-model-tier/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Codex CLI 固有の写像

PF 中立のモデル層は、Codex CLI では **`gpt-5.6` を固定したまま `model_reasoning_effort` で推論予算を写像する**。旧版の `gpt-5` へ戻さない。この写像の適用先は Codex CLI の session/config である。`.codex/agents/*.toml` は session の任意設定を継承するため、各 custom-agent TOML へ `model` や `model_reasoning_effort` を複製しない。

| PF 中立の層/予算 | Codex CLI の設定 |
|---|---|
| 低位モデル層 | `model: gpt-5.6` / `model_reasoning_effort: low` |
| 中位モデル層（小〜中） | `model: gpt-5.6` / `model_reasoning_effort: low`〜`medium` |
| 中位モデル層（大〜最大） | `model: gpt-5.6` / `model_reasoning_effort: high`〜`xhigh` |
| 最上位モデル層 | `model: gpt-5.6` / `model_reasoning_effort: xhigh` |

Codex CLI session/config 用の設定例：

```toml
model = "gpt-5.6"
model_reasoning_effort = "xhigh" # Bloom Lv5 評価・網羅性ボトルネック
```
