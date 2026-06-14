# 非機能・制約

> **型**: NFR ／ **必須上流**: SR（refines ✅）
> **必須**: FND/TC/VERIFY からの `validates` 辺が少なくとも1本（RULE-006 config）
> NFR は他ノードの refines 上流にならない。`constrains` 辺で制約先を明示する（任意）。

## [制約名]

<details><summary>⬡ NFR-001 · v0.1</summary>

```yaml
id: NFR-001
type: NFR
labels: []
scheduled: ""
edges:
  - to: SR-001          # 必須: この制約が属するステークホルダー要求
    ref_version: "0.1"
  - to: MOD-001         # 任意: 制約先（何を制約するか）
    ref_version: "0.1"
```
</details>

[制約内容・根拠を記述。例: stdlib のみ使用・fail-close 原則]

<!-- 検証証跡（FND/TC/VERIFY → この NFR に validates 辺）が必要 -->
