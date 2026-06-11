---
version: "0.3.0"
---
# 機能仕様

> **型**: SPEC ／ **必須上流**: FR（refines ✅）
> condition: normal | boundary | failure | error（RULE-016）。
> TD/検証層ノードの必須辺（RULE-015/009〜013/020/021）は `stage_scope.disable` でステージ単位に無効化する（ノード単位の suppress は付与しない）。
> 出典は各 FR と `docs/doc-system/`。

---

## SPEC-1: ノード埋め込みのパース（normal）

<details><summary>⬡ SPEC-1 · v0.2</summary>

```yaml
id: SPEC-1
type: SPEC
labels: []
scheduled: ""
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
scheduled: ""
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

## SPEC-3: ID 管理の正常系（normal）

<details><summary>⬡ SPEC-3 · v0.2</summary>

```yaml
id: SPEC-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-2
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-3-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-3-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-3-3
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

ID 採番・永続・階層分解の正常系（SPEC-3-1〜3 を参照）。

---

## SPEC-3-1: PREFIX-N[-N...] 形式の一意 ID 採番（normal）

<details><summary>⬡ SPEC-3-1 · v0.1</summary>

```yaml
id: SPEC-3-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 既存ノード集合の ID リストが判明している
**入力/トリガ**: 著者が新規ノードに ID を付与する
**期待動作**: `PREFIX-N[-N...]` 形式で既存 ID と重複しない一意な ID を採番する

---

## SPEC-3-2: ID の永続（リネームなし）（normal）

<details><summary>⬡ SPEC-3-2 · v0.1</summary>

```yaml
id: SPEC-3-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: ID を持つノードが存在する
**入力/トリガ**: ノードの見出し・本文・辺を変更する
**期待動作**: ID は変更せずに永続させる。意味は見出し（heading）が担い、ID は追跡キーとしてのみ機能する

---

## SPEC-3-3: 階層分解時の親 decomposes 辺（normal）

<details><summary>⬡ SPEC-3-3 · v0.1</summary>

```yaml
id: SPEC-3-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: `I-1-1` のような子 ID と、親 `I-1` が存在する
**入力/トリガ**: 著者が子ノードを作成する
**期待動作**: 親ノードに子へ向かう `decomposes` 辺を追加する

---

## SPEC-4: 階層 ID 親の decomposes 欠如（failure）

<details><summary>⬡ SPEC-4 · v0.2</summary>

```yaml
id: SPEC-4
type: SPEC
labels: []
scheduled: ""
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
scheduled: ""
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
scheduled: ""
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
**期待動作**: RULE-007 ERROR を報告する。`always_error` のため scheduled / stage_scope.disable / suppress いずれでも抑制不可

---

## SPEC-7: 孤立ノードの検出（failure）

<details><summary>⬡ SPEC-7 · v0.2</summary>

```yaml
id: SPEC-7
type: SPEC
labels: []
scheduled: ""
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
scheduled: ""
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
scheduled: ""
condition: failure
edges:
  - to: FR-4
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-9-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-9-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

辺の `ref_version` と参照先ファイルの version の不一致（ドリフト）検出（SPEC-9-1〜2 を参照）。

---

## SPEC-9-1: 主要辺のドリフト → RULE-004 ERROR（failure）

<details><summary>⬡ SPEC-9-1 · v0.1</summary>

```yaml
id: SPEC-9-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-9
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 辺が `ref_version` を持ち、参照先ファイルに version がある
**入力/トリガ**: `refines` / `realizes` / `verifies` 辺の `ref_version` の x.y が参照先の現在 x.y と不一致
**期待動作**: RULE-004 ERROR を報告する（主要辺のドリフトは設計反映漏れのリスクが高いため ERROR）

---

## SPEC-9-2: その他辺のドリフト → RULE-003 WARNING（failure）

<details><summary>⬡ SPEC-9-2 · v0.1</summary>

```yaml
id: SPEC-9-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-9
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 辺が `ref_version` を持ち、参照先ファイルに version がある
**入力/トリガ**: `refines` / `realizes` / `verifies` 以外の辺の `ref_version` の x.y が参照先の現在 x.y と不一致
**期待動作**: RULE-003 WARNING を報告する

---

## SPEC-10: ファイル x.y 上昇で主要辺を done→pending リセット（normal）

<details><summary>⬡ SPEC-10 · v0.2</summary>

```yaml
id: SPEC-10
type: SPEC
labels: []
scheduled: ""
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
scheduled: ""
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
scheduled: ""
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
scheduled: ""
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
scheduled: ""
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
scheduled: ""
condition: failure
edges:
  - to: FR-6
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-15-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-15-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-15-3
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

SPEC と TD のカバレッジ・condition 整合性の失敗系（SPEC-15-1〜3 を参照）。

---

## SPEC-15-1: SPEC に TD verifies 欠如（RULE-015）（failure）

<details><summary>⬡ SPEC-15-1 · v0.1</summary>

```yaml
id: SPEC-15-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-15
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: SPEC ノードが存在する
**入力/トリガ**: SPEC に TD からの `verifies` 辺がない
**期待動作**: RULE-015 WARNING を報告する

---

## SPEC-15-2: condition 属性なし・語彙外（RULE-016）（failure）

<details><summary>⬡ SPEC-15-2 · v0.1</summary>

```yaml
id: SPEC-15-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-15
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: SPEC または TD ノードが存在する
**入力/トリガ**: SPEC・TD に `condition` 属性がない、または `config.yaml` の `condition_vocab` 外の値が設定されている
**期待動作**: RULE-016 WARNING を報告する

---

## SPEC-15-3: TD の condition が verifies 先 SPEC と不一致（RULE-019）（failure）

<details><summary>⬡ SPEC-15-3 · v0.1</summary>

```yaml
id: SPEC-15-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-15
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: TD が SPEC に `verifies` 辺を持ち、両者に `condition` 属性がある
**入力/トリガ**: TD の `condition` が verifies 先 SPEC の `condition` と一致しない
**期待動作**: RULE-019 WARNING を報告する

---

## SPEC-16: FR の condition 網羅（failure）

<details><summary>⬡ SPEC-16 · v0.2</summary>

```yaml
id: SPEC-16
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-6
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-16-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-16-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

FR が保有する SPEC 群の condition 網羅の失敗系（SPEC-16-1〜2 を参照）。

---

## SPEC-16-1: FR の SPEC 群に normal condition なし（RULE-017）（failure）

<details><summary>⬡ SPEC-16-1 · v0.1</summary>

```yaml
id: SPEC-16-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-16
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: FR に SPEC 群が refines で接続されている
**入力/トリガ**: FR の SPEC 群に `condition: normal` を持つものが 1 つもない
**期待動作**: RULE-017 WARNING を報告する（正常系仕様の欠如）

---

## SPEC-16-2: FR の SPEC 群に failure/error condition なし（RULE-018）（failure）

<details><summary>⬡ SPEC-16-2 · v0.1</summary>

```yaml
id: SPEC-16-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-16
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: FR に SPEC 群が refines で接続されている
**入力/トリガ**: FR の SPEC 群に `condition: failure` も `condition: error` も存在しない
**期待動作**: RULE-018 INFO を報告する（意図的なら suppress 可）

---

## SPEC-17: 検証層の辺・属性が揃えば違反 0（normal）

<details><summary>⬡ SPEC-17 · v0.2</summary>

```yaml
id: SPEC-17
type: SPEC
labels: []
scheduled: ""
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
scheduled: ""
condition: failure
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-18-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-18-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-18-3
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-18-4
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-18-5
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

検証層ノード（FND/NFR/TC/VERIFY）の必須辺欠如（SPEC-18-1〜5 を参照）。

---

## SPEC-18-1: FND に found-in 欠如（RULE-009）（failure）

<details><summary>⬡ SPEC-18-1 · v0.1</summary>

```yaml
id: SPEC-18-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 型が FND のノードが存在する
**入力/トリガ**: FND に `found-in` 辺がない
**期待動作**: RULE-009 WARNING を報告する

---

## SPEC-18-2: FND に validates 欠如（RULE-010）（failure）

<details><summary>⬡ SPEC-18-2 · v0.1</summary>

```yaml
id: SPEC-18-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 型が FND のノードが存在する
**入力/トリガ**: FND に `validates` 辺がない
**期待動作**: RULE-010 WARNING を報告する

---

## SPEC-18-3: NFR に validates 欠如（RULE-011）（failure）

<details><summary>⬡ SPEC-18-3 · v0.1</summary>

```yaml
id: SPEC-18-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 型が NFR のノードが存在する
**入力/トリガ**: NFR に `validates` 辺がない
**期待動作**: RULE-011 WARNING を報告する

---

## SPEC-18-4: TC に realizes 欠如（RULE-012）（failure）

<details><summary>⬡ SPEC-18-4 · v0.1</summary>

```yaml
id: SPEC-18-4
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 型が TC のノードが存在する
**入力/トリガ**: TC に `realizes` 辺がない
**期待動作**: RULE-012 WARNING を報告する

---

## SPEC-18-5: VERIFY に verifies 欠如（RULE-013）（failure）

<details><summary>⬡ SPEC-18-5 · v0.1</summary>

```yaml
id: SPEC-18-5
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 型が VERIFY のノードが存在する
**入力/トリガ**: VERIFY に `verifies` 辺がない
**期待動作**: RULE-013 WARNING を報告する

---

## SPEC-19: テスト結果の完結性（failure）

<details><summary>⬡ SPEC-19 · v0.2</summary>

```yaml
id: SPEC-19
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-7
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-19-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-19-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

TR ノードの結果属性の完結性失敗系（SPEC-19-1〜2 を参照）。

---

## SPEC-19-1: TR に result 属性なし（RULE-020）（failure）

<details><summary>⬡ SPEC-19-1 · v0.1</summary>

```yaml
id: SPEC-19-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-19
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 型が TR のノードが存在する
**入力/トリガ**: TR に `result` 属性がない
**期待動作**: RULE-020 WARNING を報告する

---

## SPEC-19-2: TR result:FAIL かつ log_ref なし（RULE-021）（failure）

<details><summary>⬡ SPEC-19-2 · v0.1</summary>

```yaml
id: SPEC-19-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-19
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 型が TR のノードに `result: FAIL` が設定されている
**入力/トリガ**: TR に `log_ref` 属性がない
**期待動作**: RULE-021 WARNING を報告する（FAIL の根拠ログが必須）

---

## SPEC-20: scheduled による完全サイレント（normal）

<details><summary>⬡ SPEC-20 · v0.2</summary>

```yaml
id: SPEC-20
type: SPEC
labels: []
scheduled: ""
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
**期待動作**: そのノードに対する全ルールを発火させない（always_error 指定ルール〔RULE-007〕のみ例外）

---

## SPEC-21: stage_scope による検査無効化（normal）

<details><summary>⬡ SPEC-21 · v0.3</summary>

```yaml
id: SPEC-21
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-8
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-21-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-21-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-21-3
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-21-4
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

`config.yaml` の `stage_scope[current_stage].disable` リストに `{rule: RULE-xxx, on: NodeType}` ペアを登録することで、特定ステージで特定ノードタイプへの検査を無効化する（SPEC-21-1〜4 を参照）。

---

## SPEC-21-1: disable 対象ペアの検査サイレント（normal）

<details><summary>⬡ SPEC-21-1 · v0.1</summary>

```yaml
id: SPEC-21-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: `stage_scope[current_stage].disable` に `{rule: R, on: T}` ペアが存在する
**入力/トリガ**: type が T のノードに対してルール R を評価しようとする
**期待動作**: R の評価をスキップし、違反を報告しない

---

## SPEC-21-2: disable 非対象ペアの検査発火（normal）

<details><summary>⬡ SPEC-21-2 · v0.1</summary>

```yaml
id: SPEC-21-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: `stage_scope[current_stage].disable` に当該 `{rule: R, on: T}` ペアが含まれない
**入力/トリガ**: type が T のノードに対してルール R を評価する
**期待動作**: R を元の深刻度で評価し、違反があれば報告する

---

## SPEC-21-3: always_error は disable 対象でも発火（error）

<details><summary>⬡ SPEC-21-3 · v0.1</summary>

```yaml
id: SPEC-21-3
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-21
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: `stage_scope[current_stage].disable` に `{rule: RULE-007, on: X}` が含まれる（誤設定）
**入力/トリガ**: type が X のノードに存在しない ID への参照がある
**期待動作**: disable 設定を無視して RULE-007 ERROR を報告する（always_error のため）

---

## SPEC-21-4: current_stage が stage_scope に未定義（failure）

<details><summary>⬡ SPEC-21-4 · v0.1</summary>

```yaml
id: SPEC-21-4
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-21
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: `config.yaml` に `current_stage` が設定されている
**入力/トリガ**: `stage_scope` に `current_stage` 値に対応するキーが存在しない
**期待動作**: ツール設定エラーを報告し、stage_scope 判定をスキップして全ルールを元の深刻度で評価する

---

## SPEC-22: suppress による理由付きルール抑制（normal）

<details><summary>⬡ SPEC-22 · v0.2</summary>

```yaml
id: SPEC-22
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-8
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: ノードに `suppress: [RULE-xxx]` ＋理由インラインコメントがある
**入力/トリガ**: 検証ツールがそのノードの RULE-xxx を評価する
**期待動作**: 当該ルールをそのノードに対してのみサイレントにする

---

## SPEC-23: suppress の禁止ケース（error）

<details><summary>⬡ SPEC-23 · v0.3</summary>

```yaml
id: SPEC-23
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-8
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-23-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-23-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

suppress の禁止ケース（always_error 抑制試みと理由コメント欠如）（SPEC-23-1〜2 を参照）。

---

## SPEC-23-1: RULE-007 を suppress に含めても抑制不可（error）

<details><summary>⬡ SPEC-23-1 · v0.1</summary>

```yaml
id: SPEC-23-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-23
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: suppress 機構が動作している
**入力/トリガ**: ノードの `suppress` リストに RULE-007 が含まれる
**期待動作**: RULE-007 の抑制を無視し、存在しない ID 参照があれば常に ERROR を報告する（always_error のため）

---

## SPEC-23-2: suppress エントリに理由コメントなし（failure）

<details><summary>⬡ SPEC-23-2 · v0.1</summary>

```yaml
id: SPEC-23-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-23
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: ノードに `suppress` フィールドがある
**入力/トリガ**: suppress エントリの後に `# 理由` インラインコメントがない
**期待動作**: suppress 品質チェックの WARNING を報告する（理由なき抑制は設計品質劣化の兆候）

---

## SPEC-24: trace_scope による in-graph 判定（normal）

<details><summary>⬡ SPEC-24 · v0.2</summary>

```yaml
id: SPEC-24
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-9
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-24-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-24-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

`config.yaml` の `trace_scope.include`/`exclude` を使った in-graph ファイル集合の決定（SPEC-24-1〜2 を参照）。

---

## SPEC-24-1: include 一致・exclude 非一致 → in-graph（normal）

<details><summary>⬡ SPEC-24-1 · v0.1</summary>

```yaml
id: SPEC-24-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-24
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: `config.yaml` に `trace_scope.include` および `trace_scope.exclude`（glob）が設定されている
**入力/トリガ**: ファイルパスが include glob に一致し、exclude glob に一致しない
**期待動作**: そのファイルを in-graph として扱い、検証対象に含める

---

## SPEC-24-2: include 一致・exclude 一致 → out-of-graph（boundary）

<details><summary>⬡ SPEC-24-2 · v0.1</summary>

```yaml
id: SPEC-24-2
type: SPEC
labels: []
scheduled: ""
condition: boundary
edges:
  - to: SPEC-24
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: `config.yaml` に `trace_scope.include` および `trace_scope.exclude` が設定されている
**入力/トリガ**: ファイルパスが include glob に一致し、かつ exclude glob にも一致する
**期待動作**: exclude が include より優先されるため、そのファイルを out-of-graph として検証対象から除外する

---

## SPEC-25: 出力形式と終了コード（normal）

<details><summary>⬡ SPEC-25 · v0.2</summary>

```yaml
id: SPEC-25
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-10
    kind: refines
    status: pending
    ref_version: "0.2"
  - to: SPEC-25-1
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-25-2
    kind: decomposes
    status: pending
    ref_version: "0.3"
  - to: SPEC-25-3
    kind: decomposes
    status: pending
    ref_version: "0.3"
```
</details>

CLI の出力整列と終了コードの仕様（SPEC-25-1〜3 を参照）。

---

## SPEC-25-1: 違反一覧の深刻度順整列（normal）

<details><summary>⬡ SPEC-25-1 · v0.1</summary>

```yaml
id: SPEC-25-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-25
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 検証ツールが in-graph を走査し終えている
**入力/トリガ**: CLI を実行する
**期待動作**: 違反一覧を深刻度順（ERROR→WARNING→INFO）に整列して出力する

---

## SPEC-25-2: ERROR あり → 終了コード 1（failure）

<details><summary>⬡ SPEC-25-2 · v0.1</summary>

```yaml
id: SPEC-25-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-25
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 検証ツールが走査を完了している
**入力/トリガ**: 違反一覧に ERROR が 1 件以上含まれる
**期待動作**: 終了コード 1 を返す

---

## SPEC-25-3: ERROR なし → 終了コード 0（normal）

<details><summary>⬡ SPEC-25-3 · v0.1</summary>

```yaml
id: SPEC-25-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-25
    kind: refines
    status: pending
    ref_version: "0.3"
```
</details>

**前提条件**: 検証ツールが走査を完了している
**入力/トリガ**: 違反一覧に ERROR が 0 件
**期待動作**: 終了コード 0 を返す

---

## SPEC-26: テンプレートの必須フィールド充足（normal）

<details><summary>⬡ SPEC-26 · v0.2</summary>

```yaml
id: SPEC-26
type: SPEC
labels: []
scheduled: ""
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

## SPEC-27: エージェントが外部参照なしに著作規約を提供（normal）

<details><summary>⬡ SPEC-27 · v0.2</summary>

```yaml
id: SPEC-27
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-11
    kind: refines
    status: pending
    ref_version: "0.2"
```
</details>

**前提条件**: 型別著作エージェント（AGENT.md）が `.claude/agents/` にある
**入力/トリガ**: 著者が著作エージェントを呼び出して著作する
**期待動作**: エージェント内に型・ID PREFIX・辺・本文フォーマット・RULE チェックリストが揃い、外部ファイル読み込みなしに著作できる

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
