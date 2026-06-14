# テスト結果

> **型**: TR ／ **必須上流**: TC（produced-by ✅）
> 1 ノード = 1 実行記録。`result` と `log_ref` は機械チェック対象のため YAML メタに記載する。
> **RULE-020（ERROR）**: `result` 属性が必要（なしは ERROR）。
> **RULE-021（ERROR）**: `log_ref` は result が PASS/FAIL いずれでも必須（証跡なしは ERROR）。

## TR-001: [テスト名] — PASS / FAIL

<details><summary>⬡ TR-001 · v0.1</summary>

```yaml
id: TR-001
type: TR
result: PASS          # PASS | FAIL（必須・RULE-020 ERROR）
log_ref: ""           # ログのパスまたは URL（result 問わず必須・RULE-021 ERROR）
                      # 例: "ci/logs/run-42.txt" / "https://ci.example.com/run/42"
labels: []
scheduled: ""
edges:
  - to: TC-001          # 必須: この結果を生成したテストコード
    ref_version: "0.1"
```
</details>

**実施日**: [YYYY-MM-DD]
**コミット ID**: [ハッシュ]
**テストケースバージョン**: [TD 側 ref_version]

<!-- FAIL の場合のみ以下を記載 -->
**根本原因**: [何が原因か]
**対処**: [どう修正したか / wontfix の場合その理由]
