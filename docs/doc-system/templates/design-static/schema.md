---
version: "0.1.0"
---
# スキーマ

> **型**: SCM ／ **必須上流**: SPEC（依存辺 ✅）／TERM（任意・依存辺）

## SCM-001: [スキーマ名]

<details><summary>⬡ SCM-001 · v0.1</summary>

```yaml
id: SCM-001
type: SCM
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: このスキーマが実現する機能仕様
    ref_version: "0.1"
  - to: TERM-001        # 任意: スキーマで使う用語（無名依存辺）
    ref_version: "0.1"
```
</details>

**読み手**: [人 / プログラム / LLM]
**フロントマター**: [機械読取フィールド一覧]
**本文**: [人・LLM 向けの記述形式]
