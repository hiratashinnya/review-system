# ドキュメント検証

> **型**: VERIFY ／ **必須**: verifies 辺が1本以上（RULE-006 config）
> 検証ツール自動走査の結果、または手動レビューの記録。

## VERIFY-001: [検証名]

<details><summary>⬡ VERIFY-001 · v0.1</summary>

```yaml
id: VERIFY-001
type: VERIFY
labels: []
scheduled: ""
edges:
  - to: DM-001          # 必須: 検証対象の要素（任意の型）
    ref_version: "0.1"
  - to: NFR-001         # 任意: 証明する NFR
    ref_version: "0.1"
```
</details>

**検証手法**: [自動ツール / 手動レビュー / spec-inspector]
**実施日**: [YYYY-MM-DD]
**対象範囲**: [何を検証したか]
**結果**: [pass / fail / 指摘あり]
**発生した指摘**: [→ FND-NNN 参照]
