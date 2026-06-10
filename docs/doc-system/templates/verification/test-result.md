---
version: "0.1.0"
---
# テスト結果

> **型**: TR ／ **必須上流**: TC（produced-by ✅）
> 1 ノード = 1 実行記録。`result` と `log_ref` は機械チェック対象のため YAML メタに記載する。
> **RULE-020**: `result` 属性が必要（PASS/FAIL 不明は WARNING）。
> **RULE-021**: `result: FAIL` のとき `log_ref` が必要（失敗証跡なしは WARNING）。

## TR-001: [テスト名] — PASS / FAIL

<details><summary>⬡ TR-001 · v0.1</summary>

```yaml
id: TR-001
type: TR
result: PASS          # PASS | FAIL（RULE-020）
log_ref: ""           # ログのパスまたは URL（result: FAIL のとき必須・RULE-021）
                      # 例: "ci/logs/run-42.txt" / "https://ci.example.com/run/42"
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

<!-- FAIL の場合のみ以下を記載 -->
**根本原因**: [何が原因か]
**対処**: [どう修正したか / wontfix の場合その理由]
