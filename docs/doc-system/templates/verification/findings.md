---
version: "0.1.0"
---
# 指摘・Finding

> **型**: FND ／ **必須**: `found-in` 辺が1本以上（RULE-006 config）
> NFR 関連の指摘は `validates` 辺も必要（§11）。

## FND-001: [指摘タイトル]

<details><summary>⬡ FND-001 · v0.1</summary>

```yaml
id: FND-001
type: FND
labels: []
scheduled: ""
edges:
  - to: DM-001          # 必須: 指摘が見つかった要素
    ref_version: "0.1"
  - to: NFR-001         # 任意（NFR 関連のみ）: この指摘が証明する NFR
    ref_version: "0.1"
  - to: DD-001          # 任意: この指摘に関連する意思決定（無名依存辺）
    ref_version: "0.1"
```
</details>

**深刻度**: [ERROR / WARNING / INFO]
**内容**: [何が問題か]
**対応状況**: [open / resolved / wontfix]
**対応内容**: [どう直したか・直さない理由]
