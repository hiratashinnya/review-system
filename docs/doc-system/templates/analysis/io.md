---
version: "0.1.0"
---
# 入出力台帳

> **型**: I, O ／ **必須上流**: SPEC（refines ✅）
> **必須(§10)**:
>   I → P へのリンク（`consumes` または P 側から `consumes`）
>   O は P からの `produces` 辺を受ける
> **階層**: I-1 を I-1-1/I-1-2 に分割する場合は親に `decomposes` 辺を追加。

## 入力: [入力名]

<details><summary>⬡ I-001 · v0.1</summary>

```yaml
id: I-001
type: I
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: この入力が応える機能仕様
    kind: refines
    status: pending
    ref_version: "0.1"
  # 必須(§10): P との接続は P 側の edges に `to: I-001 / kind: consumes` を記述する
  # I 側に辺を置く場合は kind: see-also のみ（triggers は E の辺種別）
```
</details>

**発生源**: [どの外部アクタ・システムから来るか]
**内容**: [もの＋形式を記述]

---

## 出力: [出力名]

<details><summary>⬡ O-001 · v0.1</summary>

```yaml
id: O-001
type: O
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: この出力が実現する機能仕様
    kind: refines
    status: pending
    ref_version: "0.1"
  # P-001 → O-001 (produces) は P 側の edges に記述する
  # O 側は上流 SPEC への refines のみ
```
</details>

**受け手**: [どの外部アクタ・システムへ届くか]
**内容**: [もの＋形式を記述]

---

## 階層 ID の例（入力分割）

<details><summary>⬡ I-001 · v0.1（親）</summary>

```yaml
id: I-001
type: I
edges:
  - to: SPEC-001
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-001-1         # 必須: 子を decomposes で列挙
    kind: decomposes
    status: done
    ref_version: "0.1"
  - to: I-001-2
    kind: decomposes
    status: done
    ref_version: "0.1"
```
</details>
