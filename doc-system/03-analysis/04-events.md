---
version: "0.1.0"
---
# イベント

> **型**: E ／ **必須上流**: SPEC（refines ✅）
> E → P は **E 側** `kind: triggers`（P 側には書かない）。

---

## E-1: 点検要求

<details><summary>⬡ E-1 · v0.1</summary>

```yaml
id: E-1
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-1
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**イベント名**: 点検要求
**スティミュラス**: 仕様著者（ACTOR-1）またはCIが spec-inspector にノードファイル群（I-1）を渡して点検を起動する
**アクション**: P-1（パース）→ P-2（RULE検査）・P-3（カバレッジ点検）→ P-4（レポート生成）を順次実行する
**レスポンス**: O-1（RULE違反レポート）・O-2（カバレッジ点検結果）
**アフェクト**: 人手レビュー前に整合性違反と網羅性穴を機械的に可視化できる

---

## E-2: RULE 違反検出

<details><summary>⬡ E-2 · v0.1</summary>

```yaml
id: E-2
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-2
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: P-4
    kind: triggers
    status: pending
    ref_version: "0.1"
```
</details>

**イベント名**: RULE 違反検出
**スティミュラス**: P-2 が特定ノードに対する RULE 違反（RULE-007 等）を発見する（内部境界事象）
**アクション**: P-4 が違反内容をG#番号・対象ノードID・RULE番号付きでレポートに記録する
**レスポンス**: O-1（RULE違反レポート）への追記
**アフェクト**: 違反箇所が明示され、著者が修正すべき点を即座に特定できる
