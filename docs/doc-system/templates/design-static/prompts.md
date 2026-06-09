---
version: "0.1.0"
---
# プロンプトテンプレート

> **型**: PROMPT ／ **必須上流**: FR（refines ✅）
> 親テンプレートがある場合は `extends` 辺も可。ORC からは `uses` で参照される（PROMPT→ORC 辺は不要）。

## PROMPT-001: [プロンプト名]

<details><summary>⬡ PROMPT-001 · v0.1</summary>

```yaml
id: PROMPT-001
type: PROMPT
labels: []
scheduled: ""
edges:
  - to: FR-001          # 必須: このプロンプトが実現する機能仕様
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: PROMPT-000      # 任意: 継承元テンプレート
    kind: extends
    status: pending
    ref_version: "0.1"
```
</details>

**バージョン**: `MAJOR.MINOR`（MAJOR=構造/型変化・MINOR=文言のみ）
**役割制約**: [やること / やってはいけないこと]
**出力スキーマ**: [→ SCM-NNN 参照]

```
[システムプロンプト本文]
```
