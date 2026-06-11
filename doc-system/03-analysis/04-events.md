---
version: "0.3.0"
---
# イベント

> **型**: E ／ **必須上流**: SPEC（refines ✅）
> E → P は **E 側** `kind: triggers`（P 側には書かない）。

---

## E-1: 点検要求

<details><summary>⬡ E-1 · v0.2</summary>

```yaml
id: E-1
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: P-1
    kind: triggers
    status: pending
    ref_version: "0.3"
  - to: P-5
    kind: triggers
    status: pending
    ref_version: "0.3"
  - to: P-6
    kind: triggers
    status: pending
    ref_version: "0.3"
```
</details>

**イベント名**: 点検要求
**スティミュラス**: 仕様著者（ACTOR-1）またはCIが spec-inspector にノードファイル群（I-1）を渡して点検を起動する
**アクション**: P-5（設定読み込み）・P-6（in-graph集合決定）を先行実行し、P-1（パース）→ P-2（RULE検査）・P-3（カバレッジ点検）→ P-4（レポート生成）を順次実行する
**レスポンス**: O-1（RULE違反レポート）・O-2（カバレッジ点検結果）
**アフェクト**: 人手レビュー前に整合性違反と網羅性穴を機械的に可視化できる

---

## E-3: 著作要求

<details><summary>⬡ E-3 · v0.1</summary>

```yaml
id: E-3
type: E
labels: []
scheduled: ""
edges:
  - to: SPEC-26
    kind: refines
    status: pending
    ref_version: "0.3"
  - to: P-7
    kind: triggers
    status: pending
    ref_version: "0.3"
```
</details>

**イベント名**: 著作要求
**スティミュラス**: 仕様著者（ACTOR-1）が新規ノード著作を決定し、著作エージェント（P-7）を起動する
**アクション**: P-7 がテンプレート（I-7）または著作エージェント定義（I-8）を参照しノードを著作する
**レスポンス**: O-4（著作済みノードファイル）
**アフェクト**: 型・ID PREFIX・辺・本文フォーマット・RULE チェックリストが揃った状態で著作でき、規約逸脱を構造的に防止できる
