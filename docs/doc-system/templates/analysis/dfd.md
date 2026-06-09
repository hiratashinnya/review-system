---
version: "0.1.0"
---
# DFD・論理プロセス

> **型**: P ／ **必須上流**: SPEC（refines ✅）
> **必須(§10)**: I/O/E のいずれかとのリンクが1本以上
> プロセス間はI/Oノードを介して繋ぐ。P 同士を直接リンクしない（03 §7）。

## P-001: [プロセス名]

<details><summary>⬡ P-001 · v0.1</summary>

```yaml
id: P-001
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: このプロセスが実現する機能仕様
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-001           # 必須(§10): 消費する入力
    kind: consumes
    status: pending
    ref_version: "0.1"
  - to: O-001           # 必須(§10): 生成する出力
    kind: produces
    status: pending
    ref_version: "0.1"
```
</details>

**責務**: [このプロセスが行う変換・処理を1文で]
**提供価値**: [何の価値を生むか]

---

## P-001-1: [子プロセス名]（P-001 の分解）

<details><summary>⬡ P-001-1 · v0.1</summary>

```yaml
id: P-001-1
type: P
edges:
  - to: P-001           # 親プロセスへの decomposes は親側に置く
    kind: refines       # 子は親を refines する
    status: pending
    ref_version: "0.1"
  - to: I-001-1
    kind: consumes
    status: pending
    ref_version: "0.1"
```
</details>

[子プロセスの責務]
