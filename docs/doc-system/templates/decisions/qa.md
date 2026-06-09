---
version: "0.1.0"
---
# 未決論点・先送り

> **型**: Q（未決）・PEND（先送り）
> `affects` 辺 + `status: pending` は WARNING（RULE-002）。影響候補の追跡が目的。
> Q が決定されたら DD に昇格（id 通貫）。

## Q-001: [論点タイトル]

**status: open**

<details><summary>⬡ Q-001 · v0.1</summary>

```yaml
id: Q-001
type: Q
labels: []
scheduled: ""
edges:
  - to: FR-001          # 任意: 影響が懸念される要素（追跡用）
    kind: affects
    status: pending
    ref_version: "0.1"
```
</details>

**論点**: [何が未決か]
**選択肢**:
- A: [選択肢A] — [トレードオフ]
- B: [選択肢B] — [トレードオフ]

**推奨**: [推奨案と根拠]
**ブロッカー**: [決定に必要な情報・判断者]

---

## PEND-001: [先送りタイトル]

**status: deferred**

<details><summary>⬡ PEND-001 · v0.1</summary>

```yaml
id: PEND-001
type: PEND
labels: []
scheduled: "sprint-2"  # 再検討予定フェーズ
edges:
  - to: FR-002
    kind: affects
    status: n/a         # 先送り中は n/a で追跡のみ
    ref_version: "0.1"
```
</details>

**先送り理由**: [今決める必要がない根拠]
**再検討条件**: [いつ・何が揃ったら再開するか]
