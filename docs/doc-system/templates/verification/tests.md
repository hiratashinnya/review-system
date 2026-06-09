---
version: "0.1.0"
---
# テストコード

> **型**: TC ／ **必須上流**: TD（realizes ✅）
> 1 ノード = 1 テスト実装（関数 or クラス）。テスト設計（TD）をコードで実現する。
> 実行後は TR ノードを作成して結果を記録する（TR → TC (produced-by)）。

## TC-001: [テスト名]

<details><summary>⬡ TC-001 · v0.1</summary>

```yaml
id: TC-001
type: TC
labels: []
scheduled: ""
edges:
  - to: TD-001          # 必須: このコードが実現するテスト設計
    kind: realizes
    status: pending
    ref_version: "0.1"
  # TR → TC-001 (produced-by) は TR 側の edges に記述する
```
</details>

**実装ファイル**: [テストファイルパス:行番号]
**テスト関数**: [`test_xxx`]
