---
version: "0.1.0"
---
# イベントリスト

> **型**: E ／ **必須上流**: SPEC（refines ✅）
> **必須(§10)**: P への `triggers` 辺が1本以上

## E-001: [イベント名]

<details><summary>⬡ E-001 · v0.1</summary>

```yaml
id: E-001
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: このイベントが関わる機能仕様
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-001           # 必須(§10): このイベントが起動するプロセス
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**イベント名**: [イベントの短い名前]
**スティミュラス**: [外部アクタからの入力・刺激（I-# または自由記述）]
**アクション**: [システムが行う処理・行動]
**レスポンス**: [生成される出力（O-# または自由記述）]
**アフェクト**: [このイベントが生む価値・便益]
