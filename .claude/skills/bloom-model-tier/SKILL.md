---
name: bloom-model-tier
description: Assign a Claude model tier + effort level to a sub-agent's frontmatter (`model:`/`effort:`) by independently mapping the model tier and reasoning budget from the common 12-cell Bloom table (low-tier→haiku, mid-tier→sonnet, top-tier→opus; minimum/small/medium/large/maximum→`effort: low`/`medium`/`high`/`xhigh`/`xhigh`). Use when deciding which model/effort a custom agent should run on. NOT runtime control-flow or version-stamp logging (orchestration-design), NOT prompt template design (prompt-design).
---

## 共通本文

この資産の共通本文は [bloom-model-tier の共通本文](../../../.ai/skills/bloom-model-tier/SKILL.md) にあります。必ず読み、その指示に従ってください。

## Claude Code 固有の写像

PF 中立のモデル層を Claude Code の sub-agent frontmatter の `model:` に次のように写像する。モデル層と推論予算は別々に選び、すべてのモデル層で `effort:` の5段階写像を適用できる形にする。

| PF 中立のモデル層 | Claude Code の `model:` |
|---|---|
| 低位モデル層 | `haiku` |
| 中位モデル層 | `sonnet` |
| 最上位モデル層 | `opus` |

| PF 中立の予算 | Claude Code の `effort:` |
|---|---|
| 最小 | `low` |
| 小 | `medium` |
| 中 | `high` |
| 大 | `xhigh` |
| 最大 | `xhigh` |

```yaml
model: haiku
effort: low # PF中立: 低位モデル層 + 最小の推論予算
```
```yaml
model: sonnet
effort: xhigh # PF中立: 中位モデル層 + 大の推論予算
```
```yaml
model: opus
effort: xhigh # PF中立: 最上位モデル層 + 最大の推論予算
```
