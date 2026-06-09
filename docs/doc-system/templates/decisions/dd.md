---
version: "0.1.0"
---
# 意思決定ログ

> **型**: DD ／ **必須上流**: なし（横断スパイン）
> `affects` 辺の `status: pending` が反映漏れ検出の核心（RULE-001）。
> 影響先の反映が完了したら `done` に、影響なしと確認したら `n/a` に更新する。

## DD-001: [決定タイトル]

**status: decided**

<details><summary>⬡ DD-001 · v0.1</summary>

```yaml
id: DD-001
type: DD
labels: []
scheduled: ""
edges:
  - to: DM-001          # 影響先: 反映が必要な要素
    kind: affects
    status: pending     # 反映完了したら done / 影響なしなら n/a
    ref_version: "0.1"
  - to: FR-001          # 影響先: 複数あれば列挙
    kind: affects
    status: done
    ref_version: "0.1"
```
</details>

**論点**: [何を決めたか]
**選択肢**:
- A: [選択肢A] — [トレードオフ]
- B: [選択肢B] — [トレードオフ]

**決定**: [どれを選んだか・理由]
**影響範囲**: [どこに波及するか]
