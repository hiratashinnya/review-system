---
version: "0.1.0"
---
# 永続設計

> **型**: PRS ／ **必須上流**: DS（refines ✅）

## PRS-001: [永続化対象名]

<details><summary>⬡ PRS-001 · v0.1</summary>

```yaml
id: PRS-001
type: PRS
labels: []
scheduled: ""
edges:
  - to: DS-001          # 必須: 永続化するデータストア
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**保存形式**: [ファイル形式 / DB / git オブジェクト]
**パス規則**: [ディレクトリ構造・命名規則]
**トランザクション**: [書き込みの原子性・fail 時の振る舞い]
