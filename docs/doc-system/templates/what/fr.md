---
version: "0.1.0"
---
# 機能要求

> **型**: FR ／ **必須上流**: SR（refines ✅）
> 1 ノード = 「システムが持つべき機能・ユーザー価値」の単位（テスタブル粒度は SPEC で表現）。
> **RULE-017**: この FR を refines する SPEC の中に `condition: normal` が必要。
> **RULE-018**: `condition: failure` も `condition: error` も SPEC がなければ INFO。
>   意図的なら `suppress: [RULE-018]` + 理由 comment。

## [機能名]

<details><summary>⬡ FR-001 · v0.1</summary>

```yaml
id: FR-001
type: FR
labels: []
scheduled: ""
# suppress: [RULE-018]   # 意図的に負例なし: 理由をここに記載
edges:
  - to: SR-001
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

[システムが持つべき機能・ユーザー価値を1文で記述]
