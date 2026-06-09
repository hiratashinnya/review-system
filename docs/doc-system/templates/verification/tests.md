---
version: "0.1.0"
---
# テストケース（ソース向け）

> **型**: TC ／ **必須上流**: FR または SRC（verifies・直接先のみ）
> TC は FR を verifies して機能検証、または SRC を verifies してユニットテストを表す。

## TC-001: [テスト名]

<details><summary>⬡ TC-001 · v0.1</summary>

```yaml
id: TC-001
type: TC
labels: []
scheduled: ""
edges:
  - to: FR-001          # 必須: 検証対象の機能仕様（機能テストの場合）
    kind: verifies
    status: pending
    ref_version: "0.1"
  # または:
  # - to: SRC-001       # ユニットテストの場合は SRC を直接 verifies
  #   kind: verifies
  #   status: pending
  #   ref_version: "0.1"
```
</details>

**前提条件**: [テスト実行前に満たすべき状態]
**入力**: [テストデータ]
**期待値**: [期待される出力・状態変化]
**実績**: [実行結果・コミット ID・合否]
