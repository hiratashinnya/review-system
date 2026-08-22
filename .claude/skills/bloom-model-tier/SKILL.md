---
name: bloom-model-tier
description: Assign a Claude model tier + effort level to a sub-agent's frontmatter (`model:`/`effort:`) by classifying its dominant Bloom's-revised cognitive level AND whether its difficulty is thoroughness-bound or judgment-bound (Remember→haiku; Understand/Apply→sonnet; Analyze/Evaluate/Create→sonnet+high/xhigh effort if thoroughness-bound, else opus). Use when deciding which model/effort a custom agent should run on. NOT runtime control-flow or version-stamp logging (orchestration-design), NOT prompt template design (prompt-design).
---

## 共通本文

この資産の共通本文は [bloom-model-tier の共通本文](../../../.ai/skills/bloom-model-tier/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の写像

PF 中立のモデル層を Claude Code の sub-agent frontmatter に次のように写像する。

| PF 中立の層 | Claude Code の `model:` | 推論予算 |
|---|---|---|
| 低位モデル層 | `haiku` | — |
| 中位モデル層 | `sonnet` | `effort: low`〜`medium`、網羅性ボトルネックは `high`〜`xhigh` |
| 最上位モデル層 | `opus` | — |

```yaml
model: haiku # Bloom Lv1 記憶
```
```yaml
model: sonnet
effort: xhigh # Bloom Lv5 評価・網羅性ボトルネック（gap 提示のみで裁定はしない）
```
```yaml
model: opus # Bloom Lv6 創造・判断ボトルネック（曖昧な入力から新規構造を構成）
```
