# コンフィグ

> **型**: CFG ／ **必須上流**: SCM（instantiates ✅）・SPEC（refines ✅）

## CFG-001: [設定名]

<details><summary>⬡ CFG-001 · v0.1</summary>

```yaml
id: CFG-001
type: CFG
labels: []
scheduled: ""
edges:
  - to: SCM-001         # 必須: 準拠するスキーマ
    ref_version: "0.1"
  - to: SPEC-001        # 必須: この設定が実現する機能仕様
    ref_version: "0.1"
```
</details>

**ファイルパス**: [設定ファイルの場所]
**主要項目**: [設定できる項目と取りうる値]
**デフォルト**: [省略時の挙動]
