---
version: "0.1.0"
---
# 機能仕様

> **型**: FR ／ **必須上流**: SR（refines ✅）

## [機能名]

<details><summary>⬡ FR-001 · v0.1</summary>

```yaml
id: FR-001
type: FR
labels: []
scheduled: ""
edges:
  - to: SR-001          # 必須: この仕様が応える要求
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

[システムが満たすべき条件を1要求文で記述]
