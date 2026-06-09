---
version: "0.1.0"
---
# コンテキスト図・外部アクタ

> **型**: ACTOR ／ **必須上流**: SR（refines ✅）
> **必須**: I/O/P へのリンクが少なくとも1本（RULE-005: 孤立禁止）
> ACTOR → I/O へのリンクは `produces`/`consumes` で表現する（kind は `refines` ではない）。

## [アクタ名]

<details><summary>⬡ ACTOR-001 · v0.1</summary>

```yaml
id: ACTOR-001
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-001          # 必須: このアクタに関連するステークホルダー要求
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-001           # 必須(§10): I/O/P のいずれかへのリンク
    kind: produces      # アクタが入力を生成する場合
    status: pending
    ref_version: "0.1"
```
</details>

[アクタの役割・責務を記述]
