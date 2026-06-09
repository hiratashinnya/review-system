---
version: "0.1.0"
---
# モジュール構成

> **型**: MOD ／ **必須上流**: P（refines ✅）

## MOD-001: [モジュール名]

<details><summary>⬡ MOD-001 · v0.1</summary>

```yaml
id: MOD-001
type: MOD
labels: []
scheduled: ""
edges:
  - to: P-001           # 必須: このモジュールが実現する論理プロセス
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**パス**: `[package/module_path]`
**責務**: [単一責務を1文で]
**依存方向**: [依存する層 / 依存される層]
