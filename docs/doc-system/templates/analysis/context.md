# コンテキスト図・外部アクタ

> **型**: ACTOR ／ **必須上流**: SR（依存辺 ✅）
> **必須**: I/O/P との依存辺が少なくとも1本（RULE-005: 孤立禁止）
> 辺は無名依存辺。アクタとの I/O 関係は **O → ACTOR**（出力は受け手アクタに依存）・**E → ACTOR**（事象は刺激元アクタに依存）として O/E 側から張る。

## [アクタ名]

<details><summary>⬡ ACTOR-001 · v0.1</summary>

```yaml
id: ACTOR-001
type: ACTOR
labels: []
scheduled: ""
edges:
  - to: SR-001          # 必須: このアクタに関連するステークホルダー要求
    ref_version: "0.1"
  # I/O/P との接続は相手側から張る（O → ACTOR / E → ACTOR）。RULE-005 充足はそれらの被参照で満たす。
```
</details>

[アクタの役割・責務を記述]
