---
version: "0.1.0"
---
# ポート・アダプタ

> **型**: PORT ／ **必須上流**: MOD（refines ✅）

## PORT-001: [ポート名]

<details><summary>⬡ PORT-001 · v0.1</summary>

```yaml
id: PORT-001
type: PORT
labels: []
scheduled: ""
edges:
  - to: MOD-001         # 必須: このポートが属するモジュール
    ref_version: "0.1"
```
</details>

```python
class [PortName](Protocol):
    def method(self, arg: ArgType) -> ReturnType: ...
```

**方向**: [driven（外向き）/ driving（内向き）]
**実装アダプタ**: [本番 / テスト用 Fake]
