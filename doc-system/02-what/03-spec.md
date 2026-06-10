---
version: "0.1.0"
---
# 機能仕様

> **型**: SPEC ／ **必須上流**: FR（refines ✅）
> 全ノードに `scheduled: "verification"` を設定（TD 未作成につき RULE-015 をサイレント）。

---

## SPEC-1: ノードのパースと構造化（normal）

<details><summary>⬡ SPEC-1 · v0.1</summary>

```yaml
id: SPEC-1
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: ノードファイルがMarkdown＋YAMLフロントマター形式で存在する
**入力/トリガ**: spec-inspector がノードファイル群を受け取る
**期待動作**: YAMLフロントマターをパースし、id・type・edges を持つ構造化ノードとして生成する

---

## SPEC-2: 存在しない ID を参照したときの RULE-007 エラー（failure）

<details><summary>⬡ SPEC-2 · v0.1</summary>

```yaml
id: SPEC-2
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-1
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: ノードセットが読み込まれている
**入力/トリガ**: 辺の `to` に存在しない ID が指定されている
**期待動作**: RULE-007 エラーとして報告し、対象ノードIDと参照先IDを明示する

---

## SPEC-3: RULE 違反の G# 番号付き列挙（normal）

<details><summary>⬡ SPEC-3 · v0.1</summary>

```yaml
id: SPEC-3
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-2
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: ノードセットが正常にパースされている
**入力/トリガ**: spec-inspector にノードセットを渡す
**期待動作**: 全 RULE を適用し、違反をG#番号・対象ノードID・RULE番号・メッセージ付きで列挙したレポートを返す

---

## SPEC-4: suppress 指定による RULE サイレント化（normal）

<details><summary>⬡ SPEC-4 · v0.1</summary>

```yaml
id: SPEC-4
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: ノードに `suppress: [RULE-xxx] # 理由` が設定されている
**入力/トリガ**: spec-inspector がそのノードを評価する
**期待動作**: 当該 RULE をそのノードに対してサイレントにし、レポートに suppress 適用を記録する

---

## SPEC-5: suppress に理由コメントがない場合のエラー（error）

<details><summary>⬡ SPEC-5 · v0.1</summary>

```yaml
id: SPEC-5
type: SPEC
labels: []
scheduled: "verification"
condition: error
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: ノードに suppress が設定されている
**入力/トリガ**: suppress エントリにインラインコメントが存在しない
**期待動作**: spec-inspector がエラーとして報告し、suppress は適用しない

---

## SPEC-6: scheduled 設定による全 RULE サイレント化（normal）

<details><summary>⬡ SPEC-6 · v0.1</summary>

```yaml
id: SPEC-6
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-4
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: ノードに `scheduled: "phaseX"` が設定されている（空文字列以外）
**入力/トリガ**: spec-inspector がそのノードを評価する
**期待動作**: そのノードに対する全 RULE をサイレントにし、後フェーズ扱いとしてスキップする

---

## SPEC-7: ref_version ミスマッチの RULE-003/004 警告（normal）

<details><summary>⬡ SPEC-7 · v0.1</summary>

```yaml
id: SPEC-7
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-5
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 辺に ref_version が設定されており、参照先ノードにバージョン情報がある
**入力/トリガ**: ref_version の値が参照先ノードの現在バージョンと一致しない
**期待動作**: RULE-003（SPEC 側）または RULE-004（TD 側）として警告を出力し、対象辺を特定する

---

## SPEC-8: 型別テンプレートの必須フィールド充足（normal）

<details><summary>⬡ SPEC-8 · v0.1</summary>

```yaml
id: SPEC-8
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-6
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: templates/ 配下に型別テンプレートファイルが存在する
**入力/トリガ**: 著者がテンプレートを参照してノードを作成する
**期待動作**: テンプレートが id・type・edges の必須フィールドと型別本文フォーマットを含んでいる

---

## SPEC-9: スキルが外部ファイル参照なしに著作規約を提供する（normal）

<details><summary>⬡ SPEC-9 · v0.1</summary>

```yaml
id: SPEC-9
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.1"
```
</details>

**前提条件**: 工程別スキルファイル（SKILL.md）が .claude/skills/ に存在する
**入力/トリガ**: 著者がスキルを呼び出してノードを著作する
**期待動作**: スキルファイル内に型・ID PREFIX・辺・本文フォーマット・RULE チェックリストが全て含まれており、外部ファイルの読み込みなしに著作できる
