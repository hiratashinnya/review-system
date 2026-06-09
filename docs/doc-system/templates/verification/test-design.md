---
version: "0.1.0"
---
# テスト設計

> **型**: TD ／ **必須上流**: SPEC（verifies ✅）
> `TD → SPEC (verifies)` 辺がカバレッジの証跡（RULE-015 の充足辺）。
> 1 ノード = 1 テストシナリオ（等価クラス・境界値・正常/異常系 等）。

## TD-001: [テストシナリオ名]

<details><summary>⬡ TD-001 · v0.1</summary>

```yaml
id: TD-001
type: TD
labels: []
scheduled: ""
edges:
  - to: SPEC-001        # 必須: このテストが検証する機能仕様
    kind: verifies
    status: pending
    ref_version: "0.1"
  # TC → TD-001 (realizes) は TC 側の edges に記述する
```
</details>

**テスト観点**: [何を確認するか（正常系 / 境界値 / 異常系 / etc.）]
**前提条件**: [テスト実行前に揃えるべき状態]
**入力**: [テストデータ・操作手順]
**期待結果**: [合格条件（出力値・状態変化・ログ等）]
