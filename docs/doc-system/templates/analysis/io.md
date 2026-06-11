---
version: "0.1.0"
---
# 入出力台帳

> **型**: I, O ／ **必須上流**: SPEC（依存辺 ✅）
> 方向: **P → I**（プロセスは消費する入力に依存・P 側から張る）／ **O → P**（出力は生成プロセスに依存・O 側から張る）／ **O → ACTOR**（出力は受け手アクタに依存）。
> **必須(§10)**: I は P からの被参照（P → I）が1本以上。O は **O → P** と **O → ACTOR** を張る。
> 内部データフロー（系外に出ない）は新型 **D**（**D → SPEC**・**D → P**）で表す。
> **階層**: I-1 を I-1-1/I-1-2 に分割する場合、階層は ID パターン `X-N` から推論（decomposes 廃止）。

## 入力: [入力名]

<details><summary>⬡ I-001 · v0.1</summary>

```yaml
id: I-001
type: I
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: この入力が応える機能仕様
    ref_version: "0.1"
  # 必須(§10): P との接続は P 側の edges に `to: I-001`（P → I）を記述する
  # 辺は無名依存辺。I 側に追加の依存辺を置く場合も `- to: X` + ref_version のみ
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
    ref_version: "0.1"
  - to: P-001           # O → P: 生成プロセス（出力は生成プロセスに依存）
    ref_version: "0.1"
  - to: ACTOR-001       # O → ACTOR: 受け手アクタ（出力は受け手に依存）
    ref_version: "0.1"
```
</details>

**受け手**: [どの外部アクタ・システムへ届くか]
**内容**: [もの＋形式を記述]

---

## 階層 ID の例（入力分割）

> 親子関係は ID パターン `X-N`（I-001 と I-001-1 / I-001-2）から推論する（decomposes 廃止）。
> 親側に子を列挙する辺は張らない。各ノードは自身の依存先のみを無名辺で持つ。

<details><summary>⬡ I-001 · v0.1（親）</summary>

```yaml
id: I-001
type: I
edges:
  - to: SPEC-001
    ref_version: "0.1"
```
</details>
