---
version: "0.2.0"
---
# 機能仕様

> **型**: SPEC ／ **必須上流**: FR（refines ✅）
> 全ノードに `scheduled: "verification"`（TD/検証層は後着手のため RULE-015 をサイレント）。
> condition: normal | boundary | failure | error（RULE-016）。出典は各 FR と `docs/doc-system/`。

---

## SPEC-1: ノード埋め込みのパース（normal）

<details><summary>⬡ SPEC-1 · v0.2</summary>

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
    ref_version: "0.2"
```
</details>

**前提条件**: ファイルが frontmatter＋`<details><summary>⬡ PREFIX-N` ＋ YAML ブロック形式で書かれている
**入力/トリガ**: 検証ツールがファイルを読み込む
**期待動作**: summary 行の次の YAML ブロックを抽出し、id・type・labels・scheduled・edges を持つ構造化ノードを生成する

---

## SPEC-2: 記法が崩れた YAML ブロックのパース失敗（error）

<details><summary>⬡ SPEC-2 · v0.2</summary>

```yaml
id: SPEC-2
type: SPEC
labels: []
scheduled: "verification"
condition: error
edges:
  - to: FR-1
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルが読み込まれている
**入力/トリガ**: `<details>` 構文または YAML が壊れていて抽出できない
**期待動作**: 該当ファイル・行を明示してパースエラーを報告し、グラフ構築を中断（fail-close）する

---

## SPEC-3: ID 採番・永続・階層分解（normal）

<details><summary>⬡ SPEC-3 · v0.2</summary>

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
    ref_version: "0.2"
```
</details>

**前提条件**: 既存ノード集合の ID が判明している
**入力/トリガ**: 新規ノード採番、または `I-1` を `I-1-1`/`I-1-2` に分割する
**期待動作**: `PREFIX-N[-N...]` の一意 ID を与え、ID をリネームせず永続させ、親が子へ `decomposes` 辺を張る

---

## SPEC-4: 階層 ID 親の decomposes 欠如（failure）

<details><summary>⬡ SPEC-4 · v0.2</summary>

```yaml
id: SPEC-4
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-2
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: `I-1-1` のような階層 ID ノードが存在する
**入力/トリガ**: 親 `I-1` に当該子への `decomposes` 辺がない
**期待動作**: RULE-008 WARNING を報告する（親子関係の欠落）

---

## SPEC-5: 整合グラフは構造違反 0 で通過（normal）

<details><summary>⬡ SPEC-5 · v0.2</summary>

```yaml
id: SPEC-5
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: すべての辺が実在 ID を指し、必須上流辺が揃い、孤立ノードがない
**入力/トリガ**: 検証ツールが段階②（構造的完結性）を実行する
**期待動作**: 構造的違反（RULE-005/006/007/008）を 0 件として通過させる

---

## SPEC-6: 存在しない ID への参照（error・always_error）

<details><summary>⬡ SPEC-6 · v0.2</summary>

```yaml
id: SPEC-6
type: SPEC
labels: []
scheduled: "verification"
condition: error
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: ノード集合がパースされている
**入力/トリガ**: 辺の `to` が存在しない ID を指す
**期待動作**: RULE-007 ERROR を報告する。`always_error` のため scheduled/stage/suppress いずれでも抑制不可

---

## SPEC-7: 孤立ノードの検出（failure）

<details><summary>⬡ SPEC-7 · v0.2</summary>

```yaml
id: SPEC-7
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: ノード集合がパースされている
**入力/トリガ**: VAL/ACTOR/I/O/E ノードが `see-also` を除く辺を 1 本も持たない
**期待動作**: RULE-005 ERROR を報告する（孤立＝グラフ未接続）

---

## SPEC-8: 必須上流辺の欠如（failure）

<details><summary>⬡ SPEC-8 · v0.2</summary>

```yaml
id: SPEC-8
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-3
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 接続マトリクス（03）で ✅ の必須辺が定義されている
**入力/トリガ**: ノードに必須の直接の親への辺（例：SPEC→FR の refines）がない
**期待動作**: RULE-006 ERROR を報告する

---

## SPEC-9: バージョンドリフトの検出（failure）

<details><summary>⬡ SPEC-9 · v0.2</summary>

```yaml
id: SPEC-9
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-4
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 辺が `ref_version` を持ち、参照先ファイルに version がある
**入力/トリガ**: 辺の `ref_version` の x.y が参照先の現在 x.y と一致しない
**期待動作**: RULE-003 WARNING を報告し、refines/realizes/verifies の主要辺なら RULE-004 ERROR に昇格する

---

## SPEC-10: ファイル x.y 上昇で主要辺を done→pending リセット（normal）

<details><summary>⬡ SPEC-10 · v0.2</summary>

```yaml
id: SPEC-10
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-4
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: あるファイルの version の x または y が上昇する（z は不問）
**入力/トリガ**: 検証ツールが段階①を実行する
**期待動作**: そのファイルのノードを参照する refines/realizes/verifies 辺の status を done→pending に戻し、再反映を促す

---

## SPEC-11: 意思決定が全反映済みなら漏れ 0（normal）

<details><summary>⬡ SPEC-11 · v0.2</summary>

```yaml
id: SPEC-11
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-5
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: DD/Q の `affects` 辺がすべて done または n/a
**入力/トリガ**: 検証ツールが段階①（意思決定ドリフト）を実行する
**期待動作**: 反映漏れ（RULE-001/002）を 0 件として通過させる

---

## SPEC-12: DD の affects pending 残存（failure）

<details><summary>⬡ SPEC-12 · v0.2</summary>

```yaml
id: SPEC-12
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-5
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 型が DD のノードがある
**入力/トリガ**: DD の `affects` 辺に `status: pending` が残っている
**期待動作**: RULE-001 ERROR を報告する（型で判定・lifecycle パース不要）。反映完了で done、影響なしで n/a

---

## SPEC-13: Q の affects pending 残存（failure）

<details><summary>⬡ SPEC-13 · v0.2</summary>

```yaml
id: SPEC-13
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-5
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 型が Q のノードがある
**入力/トリガ**: Q の `affects` 辺に `status: pending` が残っている
**期待動作**: RULE-002 WARNING を報告する（未決論点の影響候補・ERROR には昇格しない）

---

## SPEC-14: カバレッジレポートの生成（normal）

<details><summary>⬡ SPEC-14 · v0.2</summary>

```yaml
id: SPEC-14
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-6
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: FR→SPEC→TD のグラフがパースされている
**入力/トリガ**: CLI を `--coverage` オプションで実行する
**期待動作**: FR ごとに condition 軸（normal/boundary/failure/error）で SPEC と TD の充足状況を表にしたカバレッジレポートを出力する

---

## SPEC-15: SPEC×TD カバレッジ・condition 不整合（failure）

<details><summary>⬡ SPEC-15 · v0.2</summary>

```yaml
id: SPEC-15
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-6
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: SPEC/TD ノードがある
**入力/トリガ**: SPEC に TD からの verifies 辺がない／SPEC・TD に condition 属性がない・語彙外／TD の condition が verifies 先 SPEC と不一致
**期待動作**: 順に RULE-015・RULE-016・RULE-019 を WARNING で報告する

---

## SPEC-16: FR の condition 網羅（failure）

<details><summary>⬡ SPEC-16 · v0.2</summary>

```yaml
id: SPEC-16
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-6
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: FR が SPEC 群を refines されている
**入力/トリガ**: FR の SPEC 群に `condition: normal` がない／`failure` も `error` もない
**期待動作**: RULE-017 を WARNING、RULE-018 を INFO で報告する（RULE-018 は意図的なら suppress 可）

---

## SPEC-17: 検証層の辺・属性が揃えば違反 0（normal）

<details><summary>⬡ SPEC-17 · v0.2</summary>

```yaml
id: SPEC-17
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: FND/NFR/TC/VERIFY/TR が必須辺と結果属性を揃えている
**入力/トリガ**: 検証ツールが検証層の完結性チェックを実行する
**期待動作**: RULE-009〜013・020/021 を 0 件として通過させる

---

## SPEC-18: 検証層ノードの必須辺欠如（failure）

<details><summary>⬡ SPEC-18 · v0.2</summary>

```yaml
id: SPEC-18
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 検証層ノードがある
**入力/トリガ**: FND に found-in/validates がない（RULE-009/010）／NFR に validates がない（RULE-011）／TC に realizes がない（RULE-012）／VERIFY に verifies がない（RULE-013）
**期待動作**: 該当 RULE を深刻度（ERROR/WARNING）どおりに報告する

---

## SPEC-19: テスト結果の完結性（failure）

<details><summary>⬡ SPEC-19 · v0.2</summary>

```yaml
id: SPEC-19
type: SPEC
labels: []
scheduled: "verification"
condition: failure
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 型が TR のノードがある
**入力/トリガ**: TR に `result` 属性がない／`result: FAIL` かつ `log_ref` がない
**期待動作**: 順に RULE-020・RULE-021 を WARNING で報告する（result/log_ref は YAML メタ）

---

## SPEC-20: scheduled による完全サイレント（normal）

<details><summary>⬡ SPEC-20 · v0.2</summary>

```yaml
id: SPEC-20
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-8
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: ノードの `scheduled` が `config.yaml` の phases に含まれる値
**入力/トリガ**: `index(node.scheduled) > index(current_phase)`
**期待動作**: そのノードに対する全ルールを発火させない（RULE-007 のみ例外）

---

## SPEC-21: stage_scope による ERROR→WARNING 降格（normal）

<details><summary>⬡ SPEC-21 · v0.2</summary>

```yaml
id: SPEC-21
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-8
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: `config.yaml` の `stage_scope[current_stage]` が定義されている
**入力/トリガ**: ノードの type が `current_stage.warn` に含まれる（`full` なら元の深刻度）
**期待動作**: そのノードに対する ERROR ルールを WARNING に降格して発火する

---

## SPEC-22: suppress による理由付きルール抑制（normal）

<details><summary>⬡ SPEC-22 · v0.2</summary>

```yaml
id: SPEC-22
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-8
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: ノードに `suppress: [RULE-xxx]` ＋理由 inline comment がある
**入力/トリガ**: 検証ツールがそのノードの RULE-xxx を評価する
**期待動作**: 当該ルールをそのノードに対してのみサイレントにする

---

## SPEC-23: always_error・理由なき suppress の扱い（error）

<details><summary>⬡ SPEC-23 · v0.2</summary>

```yaml
id: SPEC-23
type: SPEC
labels: []
scheduled: "verification"
condition: error
edges:
  - to: FR-8
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: suppress 機構が動作している
**入力/トリガ**: `suppress` に always_error（RULE-007）が含まれる／suppress に理由 comment がない
**期待動作**: always_error は抑制せず常に ERROR 発火。理由なき suppress は運用上 PR レビューで拒否（理由必須）

---

## SPEC-24: trace_scope による in-graph 判定（normal）

<details><summary>⬡ SPEC-24 · v0.2</summary>

```yaml
id: SPEC-24
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-9
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: `config.yaml` に `trace_scope.include`/`exclude`（glob）がある
**入力/トリガ**: 検証ツールが走査対象ファイルを決定する
**期待動作**: include に一致し exclude に一致しないファイルを in-graph とする（exclude が include より優先）

---

## SPEC-25: 終了コードと深刻度順出力（normal）

<details><summary>⬡ SPEC-25 · v0.2</summary>

```yaml
id: SPEC-25
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-10
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 検証ツールが in-graph を走査し終えている
**入力/トリガ**: CLI を実行する
**期待動作**: 違反一覧を深刻度順（ERROR→WARNING→INFO）に整列して出力し、ERROR が 1 件以上なら終了コード 1、なければ 0 を返す

---

## SPEC-26: テンプレートの必須フィールド充足（normal）

<details><summary>⬡ SPEC-26 · v0.2</summary>

```yaml
id: SPEC-26
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-11
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: `templates/<layer>/<type>.md` が存在する
**入力/トリガ**: 著者がテンプレートを複製してノードを作る
**期待動作**: テンプレートが id・type・必須 edges と型別本文フォーマットを含み、著者が必須項目を漏らさない

---

## SPEC-27: スキルが外部参照なしに著作規約を提供（normal）

<details><summary>⬡ SPEC-27 · v0.2</summary>

```yaml
id: SPEC-27
type: SPEC
labels: []
scheduled: "verification"
condition: normal
edges:
  - to: FR-11
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 工程別スキル（SKILL.md）が `.claude/skills/` にある
**入力/トリガ**: 著者がスキルを呼び出して著作する
**期待動作**: スキル内に型・ID PREFIX・辺・本文フォーマット・RULE チェックリストが揃い、外部ファイル読み込みなしに著作できる

---

## SPEC-28: SRC の @id realizes 検証（normal・post-mvp）

<details><summary>⬡ SPEC-28 · v0.2</summary>

```yaml
id: SPEC-28
type: SPEC
labels: [post-mvp]
scheduled: "post-mvp"
condition: normal
edges:
  - to: FR-12
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: ソースに `@id` アノテーションがあり、設計層に DM/PORT/ORC ノードがある
**入力/トリガ**: 段階④の検証を実行する
**期待動作**: `@id`→DM/PORT/ORC の realizes 辺を照合し、設計漏れ（実装あり・設計なし）と紐づけ漏れ（設計あり・realizes なし）を検出する
