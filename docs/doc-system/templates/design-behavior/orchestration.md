# オーケストレーション

> **型**: ORC ／ **必須上流**: P（refines ✅）
> E への直接辺は不要（E→P→ORC の推移で到達）。PROMPT は ORC 側から `uses` で参照する。

## ORC-001: [実行段名]

<details><summary>⬡ ORC-001 · v0.1</summary>

```yaml
id: ORC-001
type: ORC
labels: []
scheduled: ""
edges:
  - to: P-001           # 必須: この段が実現する論理プロセス
    ref_version: "0.1"
  - to: PROMPT-001      # 任意: この段で使うプロンプト（ORC 側から張る）
    ref_version: "0.1"
```
</details>

**入力型**: [受け取る型]
**出力型**: `StageOutcome[T]`（Result 型・fail-close）
**失敗時の振る舞い**: [fail-close の内容]
