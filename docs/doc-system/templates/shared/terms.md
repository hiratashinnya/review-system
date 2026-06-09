---
version: "0.1.0"
---
# 用語・データ辞書

> **型**: TERM ／ **必須上流**: FR（refines ✅）

## [用語名]

<details><summary>⬡ TERM-001 · v0.1</summary>

```yaml
id: TERM-001
type: TERM
labels: []
scheduled: ""
edges:
  - to: FR-001          # 必須: この用語が登場する機能仕様
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**定義**: [用語の定義を1文で]

**型情報**: [型・取りうる値・制約など]

**使用箇所**: [どの文書・コードで使われるか]
