# ドメイン型

> **型**: DM ／ **必須上流**: TERM（refines ✅）・P（refines ✅）の両方

## DM-001: [型名]

<details><summary>⬡ DM-001 · v0.1</summary>

```yaml
id: DM-001
type: DM
labels: []
scheduled: ""
edges:
  - to: TERM-001        # 必須: この型が具体化する用語
    ref_version: "0.1"
  - to: P-001           # 必須: この型を使う論理プロセス
    ref_version: "0.1"
```
</details>

```python
@dataclass(frozen=True)
class [TypeName]:
    field: FieldType
```

**不変条件**: [型が保証する制約]
**生成方法**: [コンストラクタ / ファクトリ / ビルダー・理由]
