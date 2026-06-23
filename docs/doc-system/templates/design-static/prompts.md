# プロンプトテンプレート

> **型**: PROMPT ／ **必須上流**: SPEC（refines ✅）
> 親テンプレートがある場合は `extends` 辺も可。ORC からは `uses` で参照される（PROMPT→ORC 辺は不要）。

## PROMPT-001: [プロンプト名]

<details><summary>⬡ PROMPT-001 · v0.1</summary>

```yaml
id: PROMPT-001
type: PROMPT
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: このプロンプトが実現する機能仕様
    ref_version: "0.1"
  - to: PROMPT-000      # 任意: 継承元テンプレート
    ref_version: "0.1"
```
</details>

**バージョン**: `MAJOR.MINOR.PATCH`（MAJOR=構造/型変化・MINOR=文言のみ）
**役割制約**: [やること / やってはいけないこと]
**出力スキーマ**: [→ SCM-NNN 参照]

```
[システムプロンプト本文]
```
