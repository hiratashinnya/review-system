---
version: "0.1.0"
---
# 状態・データストア

> **型**: DS ／ **必須上流**: P（refines ✅）

## DS-001: [データストア名]

<details><summary>⬡ DS-001 · v0.1</summary>

```yaml
id: DS-001
type: DS
labels: []
scheduled: ""
edges:
  - to: P-001           # 必須: この状態を必要とする論理プロセス
    ref_version: "0.1"
```
</details>

**何の状態か**: [保持する情報]
**なぜ必要か**: [毎回作れない理由・過去情報が必要な理由]
**永続性**: [永続 / セッション内 / インメモリ]
**MVP 対象**: [yes / no]
