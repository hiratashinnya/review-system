---
version: "0.1.0"
---
# テスト結果

> **型**: TR ／ **必須上流**: TC（produced-by ✅）
> 1 ノード = 1 実行記録。コミット ID・実施日・合否・ログ参照を保持する。
> 失敗時は根本原因と対処を本文に記載する。

## TR-001: [テスト名] — [PASS / FAIL]

<details><summary>⬡ TR-001 · v0.1</summary>

```yaml
id: TR-001
type: TR
labels: []
scheduled: ""
edges:
  - to: TC-001          # 必須: この結果を生成したテストコード
    kind: produced-by
    status: done
    ref_version: "0.1"
```
</details>

**実施日**: [YYYY-MM-DD]
**コミット ID**: [ハッシュ]
**テストケースバージョン**: [TD 側 ref_version]
**結果**: PASS / FAIL
**ログ**: [stdout ログへのリンクまたは抜粋]

<!-- FAIL の場合のみ以下を記載 -->
**根本原因**: [何が原因か]
**対処**: [どう修正したか / wontfix の場合その理由]
