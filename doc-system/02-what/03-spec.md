---
version: "0.3.2"
---
# 機能仕様

> **型**: SPEC ／ **必須上流**: FR または NFR（依存辺 ✅・DD-5）
> condition: normal | boundary | empty | failure | error（RULE-016 ERROR）。
> 検証層の必須接続（RULE-006 config・RULE-020/021）は `activate_stage`/`rule_activation` で verification ステージまで沈黙する（ノード単位の suppress は付与しない）。
> 出典は各 FR と `docs/doc-system/`。

---

## SPEC-1: ノード埋め込みのパース（normal）

<details><summary>⬡ SPEC-1 · v0.3</summary>

```yaml
id: SPEC-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-1
    ref_version: "0.2"
  - to: FND-14
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが1件以上存在し、当該ファイルに `<details><summary>⬡ PREFIX-N` 形式の行が存在し、その直後に ```` ```yaml ```` ブロックがあり PyYAML safe_load でパース可能である。
**入力/トリガ**: 検証ツールが当該 in-graph ファイルを処理する。
**期待動作**: `⬡` マーカー直後の YAML ブロックから `id`・`type`・`labels`・`scheduled`・`edges` を持つ構造化ノードを1件生成する。マーカー行の `PREFIX-N` と YAML の `id` 値が一致する。RULE-023〜027 の違反がなければエラー出力なし。
**例**: `doc-system/02-what/03-spec.md` 行15に `⬡ SPEC-1 · v0.3`、直後 YAML に `id: SPEC-1, type: SPEC` → ノード `{id:"SPEC-1", type:"SPEC", labels:[], scheduled:"", edges:[{to:"FR-1", ref_version:"0.2"}]}` を生成し、エラー出力なし。

---

## SPEC-2: 記法が崩れた YAML ブロックのパース失敗（error）

<details><summary>⬡ SPEC-2 · v0.3</summary>

```yaml
id: SPEC-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
  - to: FND-14
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカー行が存在し、その直後の YAML ブロック自体は存在する（マーカー欠落ではなく中身の構文不正のケース）。
**入力/トリガ**: その YAML ブロックが PyYAML safe_load で ScannerError または ParserError を発生させる（インデント不正・コロン欠如等）。
**期待動作**: `ERROR|{file}:{line}|RULE-023|(none)|YAML parse error: {例外メッセージ}` を1件出力し、当該ファイルのパースを中断する（fail-close）。後続 RULE-024〜027 を当該ファイルに発火させない。他 in-graph ファイルの処理は継続する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に不正インデント → `ERROR|doc-system/02-what/01-fr.md:17|RULE-023|(none)|YAML parse error: mapping values are not allowed here` を出力し、当該ファイルの後続ノードを生成しない。

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
    ref_version: "0.2"
```
</details>

ID 採番・永続・階層分解の正常系（SPEC-3-1〜3 を参照。階層は ID パターンで表現し親→子辺は持たない）。

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
    ref_version: "0.3"
```
</details>

**前提条件**: ID を持つノードが存在する
**入力/トリガ**: ノードの見出し・本文・辺を変更する
**期待動作**: ID は変更せずに永続させる。意味は見出し（heading）が担い、ID は追跡キーとしてのみ機能する

---

## SPEC-3-3: 階層 ID の親ノード存在（normal）

<details><summary>⬡ SPEC-3-3 · v0.1</summary>

```yaml
id: SPEC-3-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3
    ref_version: "0.3"
```
</details>

**前提条件**: `I-1-1` のような子 ID を持つノードが存在する
**入力/トリガ**: 著者が子ノードを作成する
**期待動作**: 階層は ID パターンから推論されるため親→子の辺は不要。親ノード `I-1` が存在していれば正常（decomposes 辺は廃止）

---

## SPEC-4: 階層 ID 親ノードの不在（failure）

<details><summary>⬡ SPEC-4 · v0.2</summary>

```yaml
id: SPEC-4
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-2
    ref_version: "0.2"
```
</details>

**前提条件**: `I-1-1` のような階層 ID ノードが存在する
**入力/トリガ**: 親 `I-1` ノードが存在しない（孤児階層）
**期待動作**: RULE-008 ERROR を報告する（親ノードの不在）

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
    ref_version: "0.2"
```
</details>

**前提条件**: ノード集合がパースされている
**入力/トリガ**: 辺の `to` が存在しない ID を指す
**期待動作**: RULE-007 ERROR を報告する。`always_error` のため scheduled / activate_stage / suppress いずれでも抑制不可

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
    ref_version: "0.2"
```
</details>

**前提条件**: ノード集合がパースされている
**入力/トリガ**: 任意のノードが in/out 辺を 1 本も持たない（完全孤立）
**期待動作**: RULE-005 ERROR を報告する（孤立＝グラフ未接続・always_error で抑制不可）

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
    ref_version: "0.2"
```
</details>

**前提条件**: config の `must_link_to`/`must_be_linked_from` で必須接続が定義されている
**入力/トリガ**: ノードに必須の依存辺（例：SPEC→FR）がない、または必須の被依存辺を受けていない
**期待動作**: RULE-006 をその config 行の severity（error/warning）で報告する

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
    ref_version: "0.2"
```
</details>

辺の `ref_version` と参照先ファイルの version の不一致（ドリフト）検出（SPEC-9-1〜2 を参照）。

---

## SPEC-9-1: 依存辺のドリフト → RULE-004 ERROR（failure）

<details><summary>⬡ SPEC-9-1 · v0.1</summary>

```yaml
id: SPEC-9-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-9
    ref_version: "0.3"
```
</details>

**前提条件**: 辺が `ref_version` を持ち、参照先ファイルに version がある
**入力/トリガ**: 依存辺の `ref_version` の x.y が参照先の現在 x.y と不一致
**期待動作**: RULE-004 ERROR を報告する（see-also 廃止で全辺が依存辺＝ドリフトは一律 ERROR）

---

## SPEC-9-2: 義務辺のドリフト → 決定の前提見直し（failure）

<details><summary>⬡ SPEC-9-2 · v0.1</summary>

```yaml
id: SPEC-9-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-9
    ref_version: "0.3"
```
</details>

**前提条件**: DD/Q/PEND の義務辺（`DD→X`）が `ref_version` を持つ
**入力/トリガ**: 反映前に対象 X が別件で更新され、義務辺の `ref_version` の x.y が X の現在 x.y と不一致
**期待動作**: RULE-004 ERROR を報告する（決定が古い前提に立っている＝見直しシグナル・DD-015）

---

## SPEC-10: ファイル x.y 上昇で依存辺をドリフト検出（normal）

<details><summary>⬡ SPEC-10 · v0.2</summary>

```yaml
id: SPEC-10
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-4
    ref_version: "0.2"
```
</details>

**前提条件**: あるファイルの version の x または y が上昇する（z は不問）
**入力/トリガ**: 検証ツールが段階①を実行する
**期待動作**: そのファイルのノードを参照する依存辺の `ref_version` 不一致を RULE-004 ERROR として検出し、再反映を促す（status は持たない・ref_version 更新で解消）

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
    ref_version: "0.2"
```
</details>

**前提条件**: DD/Q/PEND の義務辺がすべて削除済み（反映完了で `X→DD` の依存辺に置換済み）
**入力/トリガ**: 検証ツールが段階①（意思決定ドリフト）を実行する
**期待動作**: 反映漏れ（RULE-001/002/022）を 0 件として通過させる

---

## SPEC-12: DD の義務辺残存（failure）

<details><summary>⬡ SPEC-12 · v0.2</summary>

```yaml
id: SPEC-12
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-5
    ref_version: "0.2"
```
</details>

**前提条件**: 型が DD のノードがある
**入力/トリガ**: DD の義務辺（`DD→X`）が存在する
**期待動作**: RULE-001 ERROR を報告する（型で判定・lifecycle パース不要）。反映完了で `DD→X` を削除し `X→DD` を追加

---

## SPEC-13: Q の義務辺残存（failure）

<details><summary>⬡ SPEC-13 · v0.2</summary>

```yaml
id: SPEC-13
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-5
    ref_version: "0.2"
```
</details>

**前提条件**: 型が Q のノードがある
**入力/トリガ**: Q の義務辺（`Q→X`）が存在する
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
    ref_version: "0.2"
```
</details>

**前提条件**: FR→SPEC→TD のグラフがパースされている
**入力/トリガ**: CLI を `--coverage` オプションで実行する
**期待動作**: FR ごとに condition 軸（normal/boundary/empty/failure/error）で SPEC と TD の充足状況を表にしたカバレッジレポートを出力する

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
    ref_version: "0.2"
```
</details>

SPEC と TD のカバレッジ・condition 整合性の失敗系（SPEC-15-1〜3 を参照）。

---

## SPEC-15-1: SPEC に TD からの被依存辺欠如（RULE-006）（failure）

<details><summary>⬡ SPEC-15-1 · v0.1</summary>

```yaml
id: SPEC-15-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-15
    ref_version: "0.3"
```
</details>

**前提条件**: SPEC ノードが存在し、current_stage が verification に達している
**入力/トリガ**: SPEC に TD からの被依存辺がない（`must_be_linked_from: SPEC ← [TD]`）
**期待動作**: RULE-006 WARNING を報告する（旧 RULE-015・config 駆動）

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
    ref_version: "0.3"
```
</details>

**前提条件**: SPEC または TD ノードが存在する
**入力/トリガ**: SPEC・TD に `condition` 属性がない、または `config.yaml` の `condition_vocab` 外の値が設定されている
**期待動作**: RULE-016 ERROR を報告する（condition が無いのはダメ・未充足の RULE-017 とは別軸）

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
    ref_version: "0.2"
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
    ref_version: "0.3"
```
</details>

**前提条件**: FR に SPEC 群が接続されている
**入力/トリガ**: FR の SPEC 群に `condition: failure` も `condition: error` も存在しない
**期待動作**: RULE-018 WARNING を報告する（意図的なら suppress 可）

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
    ref_version: "0.2"
```
</details>

**前提条件**: FND/NFR/TC/VERIFY/TR が必須接続（config）と結果属性を揃えている
**入力/トリガ**: 検証ツールが検証層の完結性チェックを実行する
**期待動作**: RULE-006（config 駆動）・020/021 を 0 件として通過させる

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
    ref_version: "0.2"
```
</details>

検証層ノード（FND/NFR/TC/VERIFY）の必須辺欠如（SPEC-18-1〜5 を参照）。

---

## SPEC-18-1: FND に被指摘要素への辺欠如（RULE-006）（failure）

<details><summary>⬡ SPEC-18-1 · v0.1</summary>

```yaml
id: SPEC-18-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    ref_version: "0.3"
```
</details>

**前提条件**: 型が FND のノードが存在する（verification ステージ）
**入力/トリガ**: FND に対象要素への依存辺がない（`must_link_to: FND→any`）
**期待動作**: RULE-006 ERROR を報告する（旧 RULE-009）

---

## SPEC-18-2: TC がテスト未実行（TR 不在）（RULE-006）（failure）

<details><summary>⬡ SPEC-18-2 · v0.1</summary>

```yaml
id: SPEC-18-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    ref_version: "0.3"
```
</details>

**前提条件**: 型が TC のノードが存在する（verification ステージ）
**入力/トリガ**: TC が TR から被依存辺を受けていない（`must_be_linked_from: TC ← [TR]`＝未実行）
**期待動作**: RULE-006 WARNING を報告する（テストは実施されて初めて証跡を残す）

---

## SPEC-18-3: NFR に検証証跡の被依存辺欠如（RULE-006）（failure）

<details><summary>⬡ SPEC-18-3 · v0.1</summary>

```yaml
id: SPEC-18-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    ref_version: "0.3"
```
</details>

**前提条件**: 型が NFR のノードが存在する（verification ステージ）
**入力/トリガ**: NFR が FND/TC/VERIFY のいずれからも被依存辺を受けていない（`must_be_linked_from: NFR ← [FND,TC,VERIFY]`）
**期待動作**: RULE-006 WARNING を報告する（旧 RULE-011）

---

## SPEC-18-4: TC に TD への依存辺欠如（RULE-006）（failure）

<details><summary>⬡ SPEC-18-4 · v0.1</summary>

```yaml
id: SPEC-18-4
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    ref_version: "0.3"
```
</details>

**前提条件**: 型が TC のノードが存在する（verification ステージ）
**入力/トリガ**: TC に TD への依存辺がない（`must_link_to: TC→TD`）
**期待動作**: RULE-006 ERROR を報告する（旧 RULE-012）

---

## SPEC-18-5: VERIFY に対象要素への依存辺欠如（RULE-006）（failure）

<details><summary>⬡ SPEC-18-5 · v0.1</summary>

```yaml
id: SPEC-18-5
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-18
    ref_version: "0.3"
```
</details>

**前提条件**: 型が VERIFY のノードが存在する（verification ステージ）
**入力/トリガ**: VERIFY に対象要素への依存辺がない（`must_link_to: VERIFY→any`）
**期待動作**: RULE-006 ERROR を報告する（旧 RULE-013）

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
    ref_version: "0.2"
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
    ref_version: "0.3"
```
</details>

**前提条件**: 型が TR のノードが存在する
**入力/トリガ**: TR に `result` 属性がない
**期待動作**: RULE-020 ERROR を報告する（PASS/FAIL 不明＝結果なき報告）

---

## SPEC-19-2: TR に log_ref なし（result 問わず）（RULE-021）（failure）

<details><summary>⬡ SPEC-19-2 · v0.1</summary>

```yaml
id: SPEC-19-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-19
    ref_version: "0.3"
```
</details>

**前提条件**: 型が TR のノードが存在する（result は PASS/FAIL いずれでも）
**入力/トリガ**: TR に `log_ref` 属性がない
**期待動作**: RULE-021 ERROR を報告する（ログはノード化しない＝log_ref が唯一の証跡。証跡なき報告は不可）

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
    ref_version: "0.2"
```
</details>

**前提条件**: ノードの `scheduled` が `config.yaml` の phases に含まれる値
**入力/トリガ**: `index(node.scheduled) > index(current_phase)`
**期待動作**: そのノードに対する全ルールを発火させない（always_error 指定ルール〔RULE-007〕のみ例外）

---

## SPEC-21: ステージ発火による検査制御（normal）

<details><summary>⬡ SPEC-21 · v0.3</summary>

```yaml
id: SPEC-21
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-8
    ref_version: "0.2"
```
</details>

`config.yaml` の `activate_stage`（必須接続）/`rule_activation`（属性ルール）で各ルールの発火開始ステージを設定し、current_stage 未達のルールを沈黙させる（SPEC-21-1〜4 を参照）。

---

## SPEC-21-1: 発火ステージ未達のルールはサイレント（normal）

<details><summary>⬡ SPEC-21-1 · v0.1</summary>

```yaml
id: SPEC-21-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

**前提条件**: ルール R の発火ステージ（`activate_stage`/`rule_activation`）が定義されている
**入力/トリガ**: `index(current_stage) < index(R の発火ステージ)`
**期待動作**: R の評価をスキップし、違反を報告しない

---

## SPEC-21-2: 発火ステージ到達でルール発火（normal）

<details><summary>⬡ SPEC-21-2 · v0.1</summary>

```yaml
id: SPEC-21-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

**前提条件**: ルール R の発火ステージが定義されている
**入力/トリガ**: `index(current_stage) >= index(R の発火ステージ)`
**期待動作**: R を元の深刻度で評価し、違反があれば報告する

---

## SPEC-21-3: always_error は発火ステージ前でも発火（error）

<details><summary>⬡ SPEC-21-3 · v0.1</summary>

```yaml
id: SPEC-21-3
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

**前提条件**: `always_error` に RULE-007（および RULE-005）が登録されている
**入力/トリガ**: 存在しない ID 参照（または完全孤立）が、発火ステージや suppress の有無に関わらず存在する
**期待動作**: 抑制設定を無視して RULE-007（/RULE-005）ERROR を報告する（always_error のため）

---

## SPEC-21-4: current_stage が stages に未定義（failure）

<details><summary>⬡ SPEC-21-4 · v0.1</summary>

```yaml
id: SPEC-21-4
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-21
    ref_version: "0.3"
```
</details>

**前提条件**: `config.yaml` に `current_stage` が設定されている
**入力/トリガ**: `stages` リストに `current_stage` 値が存在しない
**期待動作**: ツール設定エラーを報告し、ステージ発火判定をスキップして全ルールを元の深刻度で評価する

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
    ref_version: "0.2"
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
    ref_version: "0.3"
```
</details>

**前提条件**: suppress 機構が動作している
**入力/トリガ**: ノードの `suppress` リストに RULE-007 が含まれる
**期待動作**: RULE-007 の抑制を無視し、存在しない ID 参照があれば常に ERROR を報告する（always_error。RULE-005 も同様）

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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.3"
```
</details>

**前提条件**: 検証ツールが走査を完了している
**入力/トリガ**: 違反一覧に ERROR が 0 件
**期待動作**: 終了コード 0 を返す

---

## SPEC-26: テンプレートの必須フィールド充足（normal）

<details><summary>⬡ SPEC-26 · v0.3</summary>

```yaml
id: SPEC-26
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-11
    ref_version: "0.2"
  - to: FND-14
    ref_version: "0.1"
```
</details>

**前提条件**: `templates/<layer>/<type>.md` が存在する（layer ∈ {requirements, analysis, design, verification}、type はその層の型名。例 `templates/requirements/SPEC.md`）。
**入力/トリガ**: 著者がテンプレートを複製してノード著作を開始する。
**期待動作**: テンプレートが以下を全て含む — `id:`（プレースホルダ）、`type:`（型名）、`labels: []`、`scheduled: ""`、`edges:`（≥1エントリ・各エントリに `to:` と `ref_version:`）、本文4項目（`**前提条件**:`／`**入力/トリガ**:`／`**期待動作**:`／`**例**:`）。複製した初期状態で RULE-025／026／027 が発火しない。
**例**: `templates/requirements/SPEC.md` を複製すると `id: SPEC-XXX`（プレースホルダ）・`type: SPEC`・`edges: [{to: FR-XX, ref_version: "0.0"}]` が存在し、複製直後のノードに対し RULE-025／026／027 がいずれも発火しない。

---

## SPEC-27: 著作エージェントが外部参照なしに著作規約を提供（normal）

<details><summary>⬡ SPEC-27 · v0.3</summary>

```yaml
id: SPEC-27
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-13
    ref_version: "0.2"
  - to: FND-14
    ref_version: "0.1"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義（例 `requirements-author.md`）が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: エージェントが外部ファイル参照なしに以下を全て提供する — 対象型の `type` 値・`id` PREFIX パターン・必須辺方向（`to` 先の型と方向）・本文4項目フォーマット・RULE チェックリスト。出力は `tmp/<sprint>/<parent-id>.md` に書かれ、reconciliation が本ファイルへ転記する。
**例**: `requirements-author` に FR 著作を依頼 → `type: FR`・`edges[].to: SR-*`（SR 辺必須）・4項目本文の指示がエージェント定義に内包され、`config.yaml` や `authoring-guide.md` を読まずに著作できる。

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
    ref_version: "0.2"
```
</details>

**前提条件**: ソースに `@id` アノテーションがあり、設計層に DM/PORT/ORC ノードがある
**入力/トリガ**: 段階④の検証を実行する
**期待動作**: `@id`→DM/PORT/ORC の realizes 辺を照合し、設計漏れ（実装あり・設計なし）と紐づけ漏れ（設計あり・realizes なし）を検出する

---

## SPEC-29: グラフ網羅性点検の正常系（normal）

<details><summary>⬡ SPEC-29 · v0.1</summary>

```yaml
id: SPEC-29
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-3
    ref_version: "0.2"
  - to: FND-4
    ref_version: "0.1"
```
</details>

**前提条件**: 全 I/O/D/P/E ノードが適切な接続を持つ（O→P・O→ACTOR・D→P・E→ACTOR・P→I/D/E の各依存辺、および I←P・D←P・E←P の被依存辺が揃っている）
**入力/トリガ**: 検証ツールがグラフ網羅性点検（P-3-1）を実行する
**期待動作**: 孤立ノード（RULE-005）・必須辺欠如（RULE-006 config の analysis 段接続）をゼロ件として通過させ、グラフが価値経路（VAL まで到達可能）と分析層接続を完全に満たすと判定する

---

## SPEC-30: 分析ノードの接続漏れ検出（failure）

<details><summary>⬡ SPEC-30 · v0.1</summary>

```yaml
id: SPEC-30
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-3
    ref_version: "0.2"
  - to: FND-4
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph に分析層ノード（I/O/D/P/E）が存在する
**入力/トリガ**: P-3-1 がグラフ網羅性を確認する際に、O に P への依存辺がない・E に P からの被依存辺がない・I に P からの被依存辺がないノードを検出する
**期待動作**: 未駆動出力（O→P 欠如）・未定義反応イベント（E←P 欠如）・未消費入力（I←P 欠如）を RULE-006 の config `activate_stage: analysis` 行の severity（error/warning）として報告する（SPEC-8 の一般則における分析層の特殊ケース）

---

## SPEC-31: trace_scope による in-graph 0 件（empty）

<details><summary>⬡ SPEC-31 · v0.1</summary>

```yaml
id: SPEC-31
type: SPEC
labels: []
scheduled: ""
condition: empty
edges:
  - to: FR-1
    ref_version: "0.2"
  - to: FND-13
    ref_version: "0.1"
```
</details>

**前提条件**: `config.yaml` の `trace_scope` 設定の結果、in-graph ファイルが0件になる。
**入力/トリガ**: 検証ツールを実行する。
**期待動作**: 違反0件・ノード0件を報告し、終了コード 0 で終了する。RULE-005〜027 の評価を全てスキップする。
**例**: `trace_scope.include: ["doc-system/**/*.md"]` かつ `exclude: ["doc-system/**/*.md"]` → in-graph ファイル0件・ノード0件・違反0件・終了コード 0。

---

## SPEC-32: ⬡ マーカー直後に YAML ブロックなし（error・RULE-024）

<details><summary>⬡ SPEC-32 · v0.1</summary>

```yaml
id: SPEC-32
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカー行が1件以上存在する。
**入力/トリガ**: `⬡` マーカー行の直後行が ```` ```yaml ```` ブロック開始行でない（heading／空行＋heading／別の `⬡` マーカーが直後に来る）。
**期待動作**: `ERROR|{file}:{line}|RULE-024|(none)|⬡ marker at line N has no YAML block following` を出力し、当該ファイルのパースを中断する（fail-close）。
**例**: `doc-system/03-analysis/02-io.md` 行20に `⬡ I-1 · v0.3`、行21が `## I-2:` → `ERROR|doc-system/03-analysis/02-io.md:20|RULE-024|(none)|⬡ marker at line 20 has no YAML block following`。

---

## SPEC-33: id フィールド欠如・空（error・RULE-025）

<details><summary>⬡ SPEC-33 · v0.1</summary>

```yaml
id: SPEC-33
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと直後の YAML ブロックが存在し、YAML は PyYAML safe_load でパース可能である。
**入力/トリガ**: YAML ブロックに `id` キーが存在しない、または値が空文字列（`id: ""`）である。
**期待動作**: `ERROR|{file}:{line}|RULE-025|(none)|id field missing or empty` を出力し、当該ノードの後続 RULE 評価を中断する（他ファイル・他ノードは継続）。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に id キーなし → `ERROR|doc-system/02-what/01-fr.md:17|RULE-025|(none)|id field missing or empty`。

---

## SPEC-34: type フィールド欠如・空（error・RULE-026）

<details><summary>⬡ SPEC-34 · v0.1</summary>

```yaml
id: SPEC-34
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと YAML ブロックが存在し、YAML パース可能で `id` キーは存在する。
**入力/トリガ**: YAML ブロックに `type` キーが存在しない、または値が空文字列である。
**期待動作**: `ERROR|{file}:{line}|RULE-026|{id}|type field missing or empty` を出力し、当該ノードの後続 RULE 評価を中断する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に type なし・id は `FR-1` → `ERROR|doc-system/02-what/01-fr.md:17|RULE-026|FR-1|type field missing or empty`。

---

## SPEC-35: edge に ref_version 欠如（failure・RULE-027）

<details><summary>⬡ SPEC-35 · v0.1</summary>

```yaml
id: SPEC-35
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルに YAML ブロックが存在し、`id`・`type` は存在する。`edges` リストに1件以上のエントリがある。
**入力/トリガ**: `edges` の任意のエントリに `ref_version` キーが存在しない。
**期待動作**: `ERROR|{file}:{line}|RULE-027|{id}|edge to {target_id}: ref_version missing` を出力し、当該ノードの後続 RULE 評価を中断する。
**例**: `doc-system/02-what/03-spec.md` の SPEC-1 ノードの edges に `{to: FR-1}`（ref_version なし）→ `ERROR|doc-system/02-what/03-spec.md:22|RULE-027|SPEC-1|edge to FR-1: ref_version missing`。

---

## SPEC-36: テンプレート由来の必須フィールド欠如（failure）

<details><summary>⬡ SPEC-36 · v0.1</summary>

```yaml
id: SPEC-36
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-11
    ref_version: "0.2"
```
</details>

**前提条件**: テンプレート `templates/<layer>/<type>.md` の `id:` または `type:` フィールドが削除されている、または空になっている。
**入力/トリガ**: 著者がそのテンプレートを複製してノードを著作し、検証ツールが当該ノードを処理する。
**期待動作**: テンプレート由来で必須フィールドを欠くため、RULE-025（id 欠如）または RULE-026（type 欠如）の ERROR が報告される。
**例**: `templates/requirements/FR.md` の `id:` 行が削除 → 著者が複製して `doc-system/02-what/01-fr.md` 行14に著作 → `ERROR|doc-system/02-what/01-fr.md:14|RULE-025|(none)|id field missing or empty`。

---

## SPEC-38: 著作エージェントが規約準拠ノードを tmp 出力（normal）

<details><summary>⬡ SPEC-38 · v0.1</summary>

```yaml
id: SPEC-38
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-13
    ref_version: "0.2"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義（例 `requirements-author.md`）が存在し、著者が FR 著作を依頼する。
**入力/トリガ**: 著者が `requirements-author` エージェントに FR ノード1件の著作を依頼する。
**期待動作**: エージェントは `type: FR`・`id: FR-N`（連番）・`edges: [{to: SR-*, ref_version: "..."}]`・本文4項目を含むノードを `tmp/sprint-1/<parent-id>.md` に出力する。出力後、reconciliation が本ファイルに転記する。
**例**: `requirements-author` に「FR-13 著作」を依頼 → `tmp/sprint-1/fr-11-13-14.md` に `id: FR-13, type: FR, edges: [{to: SR-1, ref_version: "0.2"}]` ＋4項目本文が出力される。

---

## SPEC-39: 著作出力の id 欠如を reconciliation が検出（failure）

<details><summary>⬡ SPEC-39 · v0.1</summary>

```yaml
id: SPEC-39
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-13
    ref_version: "0.2"
```
</details>

**前提条件**: 著者がエージェントに著作を依頼し、エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力する。
**入力/トリガ**: reconciliation エージェントが tmp ファイルを検証する際に、id フィールドの欠如を検出する。
**期待動作**: reconciliation は検証エラーを報告し、本ファイルへの転記を中断する。`id field missing or empty` を出力する（RULE-025 相当のチェックを reconciliation 検証フェーズで実施）。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → `ERROR|tmp/sprint-1/fr-11-13-14.md:5|RULE-025|(none)|id field missing or empty` を報告し、本ファイルへの転記を中断する。

---

## SPEC-40: 伝搬編集支援の表示（normal・post-mvp）

<details><summary>⬡ SPEC-40 · v0.1</summary>

```yaml
id: SPEC-40
type: SPEC
labels: [post-mvp]
scheduled: "post-mvp"
condition: normal
edges:
  - to: FR-14
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイル A の version x.y が上昇し、ノード B が `to: A, ref_version: "旧 x.y"` の辺を持つ（RULE-004 ドリフト状態）。
**入力/トリガ**: 著者が `--propagate A` オプションで検証ツールを実行する（post-MVP 機能）。
**期待動作**: RULE-004 ドリフトが検出されたノード B の一覧と、各ノードで更新が必要な `ref_version` の現在値・更新先値を表形式で出力する。`{node-id} | {file}:{line} | ref_version: "{old}" → "{new}"` 形式で表示する。
**例**: `doc-system/03-analysis/02-io.md` の version が `0.5`→`0.6` に上昇したとき `P-1 | doc-system/03-analysis/03-processes.md:26 | ref_version: "0.5" → "0.6"` の一覧を出力する。

---

## SPEC-41: I-1 フォーマット完全フィールドスキーマ（normal）

<details><summary>⬡ SPEC-41 · v0.1</summary>

```yaml
id: SPEC-41
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-1
    ref_version: "0.2"
  - to: FND-18
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが1件以上存在し、当該ファイルの `⬡` YAML ブロックに `id`・`type` フィールドが存在し PyYAML safe_load でパース成功している（SPEC-1 の正常系が先行している）。
**入力/トリガ**: 検証ツールが当該ノードの YAML フィールドセットを完全スキーマ定義と照合する。
**期待動作**: 全ノード型共通の必須フィールド（`id`・`type`・`labels`・`scheduled`・`edges`）が全て存在し、`labels` は配列・`scheduled` は文字列・`edges` は配列（空配列可）として検証を通過する。定義外キーが存在する場合は WARNING を1件出力するが ERROR にはならない。
**例**: `{id: "SPEC-1", type: "SPEC", labels: [], scheduled: "", edges: [{to: "FR-1", ref_version: "0.2"}]}` → 必須フィールド全て存在・型正常 → 違反 0 件。`{id: "SPEC-99", type: "SPEC", labels: [], scheduled: "", edges: [], unknown_key: "foo"}` → `WARNING|doc-system/02-what/03-spec.md:{line}|RULE-028|SPEC-99|unknown field: unknown_key` を1件出力。

---

## SPEC-42: O-2 カバレッジテーブル出力フォーマット（normal）

<details><summary>⬡ SPEC-42 · v0.1</summary>

```yaml
id: SPEC-42
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-3
    ref_version: "0.2"
  - to: FND-18
    ref_version: "0.1"
```
</details>

**前提条件**: FR→SPEC グラフがパースされており、FR が1件以上存在する。`--coverage` オプションが指定されている。
**入力/トリガ**: 検証ツールを `--coverage` オプション付きで実行する。
**期待動作**: FR 単位の表形式カバレッジが以下フォーマットで stdout に出力される。ヘッダ行 `FR-id | normal | boundary | empty | failure | error` の後、FR を id 昇順でソートした行 `{FR-id} | {✅/⬜} | {✅/⬜} | {✅/⬜} | {✅/⬜} | {✅/⬜}`（✅=SPEC あり・⬜=なし）が続く。カバレッジ欠如がある FR については別セクションに `G{N}|{FR-id}|{condition}|coverage missing` を列挙する。
**例**: FR-1 に `condition: normal` の SPEC のみ存在する場合 → `FR-1 | ✅ | ⬜ | ⬜ | ⬜ | ⬜` が出力され、gap セクションに `G1|FR-1|boundary|coverage missing`・`G2|FR-1|empty|coverage missing`・`G3|FR-1|failure|coverage missing`・`G4|FR-1|error|coverage missing` が列挙される。

---

## SPEC-43: I-7 テンプレートファイルの必須構造（normal）

<details><summary>⬡ SPEC-43 · v0.1</summary>

```yaml
id: SPEC-43
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-11
    ref_version: "0.2"
  - to: FND-18
    ref_version: "0.1"
```
</details>

**前提条件**: `templates/<layer>/<type>.md` 形式のテンプレートファイルが存在する（layer ∈ {requirements, analysis, design, verification}）。テンプレートファイル自体は `trace_scope.exclude` により in-graph 検証対象外である。
**入力/トリガ**: reconciliation エージェントが著作エージェント起動時に当該テンプレートファイルを SPEC-43 の基準で検証する。
**期待動作**: テンプレートファイルが以下を全て含む場合に検証を通過する — `id:` プレースホルダ（`id: <PREFIX>-N` 形式）・`type:` フィールド・`edges:` セクション（最低1件の辺プレースホルダ）。さらに SPEC・TD 用テンプレートには `condition:` フィールドが存在し、TR 用テンプレートには `result:` と `log_ref:` フィールドが存在する。いずれかの必須構造が欠如している場合は検証エラー1件を出力する。
**例**: `templates/requirements/SPEC.md` が `id: <SPEC-N>`・`type: SPEC`・`edges: [{to: FR-XX, ref_version: "0.0"}]`・`condition: normal` を全て含む → 必須構造充足 → 検証通過。`templates/verification/TR.md` に `result:` フィールドが存在しない → `ERROR|templates/verification/TR.md|template-check|(none)|required field missing: result` を出力。

---

## SPEC-44: ノードファイルはプレーンテキスト .md（normal）

<details><summary>⬡ SPEC-44 · v0.1</summary>

```yaml
id: SPEC-44
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-1
    ref_version: "0.2"
```
</details>

**前提条件**: `trace_scope.include` に一致する in-graph ファイルが1件以上存在する。
**入力/トリガ**: 検証ツールが in-graph ファイルを読み込む際に UTF-8 エンコードのプレーンテキスト検証を実行する。
**期待動作**: `file.read_text(encoding='utf-8', errors='strict')` で全 in-graph ファイルの読み込みがエラーなく完了する。BOM（`\xEF\xBB\xBF`）が先頭に存在するファイルは WARNING を1件出力する。UTF-8 デコードエラーが発生するファイルは ERROR を1件出力する。
**例**: `doc-system/02-what/01-fr.md` を `open(..., encoding='utf-8', errors='strict').read()` → 読み込み成功 → 違反 0 件。バイナリデータを含むファイル `doc-system/corrupt.md` が in-graph に存在 → `ERROR|doc-system/corrupt.md:0|NFR-1-check|(none)|UTF-8 decode error` を出力。

---

## SPEC-45: spec-inspector は Python 標準ライブラリのみ使用（normal）

<details><summary>⬡ SPEC-45 · v0.1</summary>

```yaml
id: SPEC-45
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-2
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector の実装ソースファイル群（`src/` 以下または実装ファイル群）が1件以上存在する。
**入力/トリガ**: reconciliation または CI が全ソースファイルの `import` 文を静的解析する。
**期待動作**: 全 `import X` 文および `from X import Y` 文が Python 標準ライブラリモジュール（`sys`, `os`, `re`, `pathlib`, `json`, `typing`, `collections`, `itertools`, `functools`, `dataclasses` 等）のみを参照する。`import yaml`（PyYAML）・`import requests`・`import pydantic` 等の外部パッケージへの依存が 0 件である。
**例**: `src/inspector.py` の全 import が `import sys`, `import os`, `import re`, `import pathlib`, `import json` のみ → 外部依存 0 件 → 検証通過。`import yaml` が `src/parser.py` 行3に存在 → `ERROR|src/parser.py:3|NFR-2-check|(none)|external package import: yaml` を出力。

---

## SPEC-46: スキルファイルは外部ファイル参照なしに自己完結（normal）

<details><summary>⬡ SPEC-46 · v0.1</summary>

```yaml
id: SPEC-46
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-3
    ref_version: "0.2"
```
</details>

**前提条件**: `.claude/skills/*/SKILL.md` または `.claude/skills/*/*.md` のスキルファイルが1件以上存在する。
**入力/トリガ**: reconciliation または asset-auditor がスキルファイルの全行を外部参照パターン（`\.\./`・`^include:`・`^source:`・`@import`）で検索する。
**期待動作**: 各スキルファイルの本文に外部ファイル参照パターン（相対パス `../`・`include:`・`source:`・`@import`）が存在しない。各パターンにマッチする行が 0 件であることを確認し、検証を通過する。
**例**: `.claude/skills/spec-author/SKILL.md` を全行検索 → `../`・`include:`・`source:`・`@import` にマッチする行なし → 検証通過。`.claude/skills/spec-author/SKILL.md` 行42に `see: ../07-authoring-guide.md` が存在 → `WARNING|.claude/skills/spec-author/SKILL.md:42|NFR-3-check|(none)|external file reference: ../07-authoring-guide.md` を出力。

---

## SPEC-47: 全 in-graph ファイルの frontmatter に version フィールドが存在（normal）

<details><summary>⬡ SPEC-47 · v0.1</summary>

```yaml
id: SPEC-47
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-4
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイルが1件以上存在する。各ファイルは `---` で囲まれた YAML frontmatter を先頭に持つことが期待される。
**入力/トリガ**: 検証ツールが in-graph 全ファイルの YAML frontmatter を読み込み、`version` フィールドを検査する。
**期待動作**: 全 in-graph ファイルの frontmatter に `version:` フィールドが存在し、値が `"x.y.z"` 形式（x・y・z はそれぞれ非負整数・例: `"0.3.1"`）の文字列である。`version:` フィールドが存在しない・空文字・null のいずれかに該当するファイルは version 欠如として ERROR を1件出力する。
**例**: `doc-system/02-what/03-spec.md` の frontmatter に `version: "0.3.2"` → `x=0, y=3, z=2`・形式適合 → 違反なし。`doc-system/02-what/01-fr.md` の frontmatter に `version:` キーが存在しない → `ERROR|doc-system/02-what/01-fr.md:1|NFR-4-check|(none)|version field missing` を出力。

---

## SPEC-48: 各ノードは直接の親のみへ辺を張る（USDM 1段制約）（normal）

<details><summary>⬡ SPEC-48 · v0.1</summary>

```yaml
id: SPEC-48
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-5
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に SPEC ノードが1件以上存在し、全ノードがパース済みである。接続マトリクスで SPEC の直接親は FR または別 SPEC と定義されている。
**入力/トリガ**: 検証ツールが SPEC ノードの `edges[].to` を走査し、祖先型（SR・VAL 等）への直接辺を検出する。
**期待動作**: SPEC ノードの `edges[].to` が全て FR・NFR・または別 SPEC（直接親 SPEC）を指し、SR・VAL などの祖先型を直接参照する辺が 0 件である。祖先型への直接辺が検出された場合は ERROR を1件出力する。
**例**: `SPEC-41` の edges が `[{to: "FR-1", ref_version: "0.2"}]` → 直接親 FR-1 のみ参照 → 違反なし。仮に `SPEC-99` の edges に `{to: "SR-2", ref_version: "0.2"}` が含まれる → `ERROR|{file}:{line}|NFR-5-check|SPEC-99|direct ancestor edge to SR-2 violates 1-level constraint` を出力。

---

## SPEC-49: DD/Q/PEND の frontmatter に status 系フィールドが存在しない（normal）

<details><summary>⬡ SPEC-49 · v0.1</summary>

```yaml
id: SPEC-49
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-6
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に `type: DD`・`type: Q`・`type: PEND` のいずれかのノードが1件以上存在する。
**入力/トリガ**: 検証ツールが DD・Q・PEND ノードの YAML フィールドキー一覧を検査する。
**期待動作**: DD・Q・PEND ノードの YAML フィールドに `status:`・`lifecycle:`・`state:` キーが存在しない。これらのキーが frontmatter に存在する場合は WARNING を1件出力する。ライフサイクル状態は本文見出しバッジ（`**status: open**` 等）にのみ記載されている。
**例**: `{id: "DD-5", type: "DD", labels: [], scheduled: "", edges: []}` → status 系フィールドなし → 違反なし。`{id: "Q-3", type: "Q", labels: [], scheduled: "", status: "open", edges: []}` → `WARNING|{file}:{line}|NFR-6-check|Q-3|lifecycle field 'status' in frontmatter violates NFR-6` を出力。

---

## SPEC-50: --export-graph による依存グラフファイル出力（normal）

<details><summary>⬡ SPEC-50 · v0.1</summary>

```yaml
id: SPEC-50
type: SPEC
labels: [post-mvp]
scheduled: ""
condition: normal
edges:
  - to: FR-15
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector がノードグラフを正常にパース済みである（SPEC-1 の正常系が先行している）。グラフに1件以上のノードが存在する。`--export-graph` オプションに有効なフォーマット名（`dot` または `json`）と出力先ファイルパスが指定されている。
**入力/トリガ**: `spec-inspector --export-graph dot ./output/graph.dot`（または `json` フォーマット・任意の出力先パス）を実行する。
**期待動作**: 指定されたフォーマット（`dot` の場合は Graphviz dot 形式・`json` の場合は JSON 隣接リスト形式）でノード間の依存関係グラフが指定ファイルパスに書き出される。stdout にはエラーメッセージを出力せず、exit code 0 で正常終了する。
**合格例**: ノード 3 件（SPEC-1→FR-1、FR-1→SR-1）を含むグラフに対して `--export-graph dot ./graph.dot` を実行 → `./graph.dot` に `digraph { "SPEC-1" -> "FR-1"; "FR-1" -> "SR-1"; }` 形式の dot ファイルが生成され、exit code 0 で終了する。
**違反例**: `--export-graph dot ./graph.dot` を実行したが出力ファイルが生成されない・または dot 形式の構文として不正なテキスト（例: JSON 形式）が書き出される → 期待動作を満たさない。

---

## SPEC-51: --complexity による参照関係複雑度メトリクスレポート stdout 出力（normal）

<details><summary>⬡ SPEC-51 · v0.1</summary>

```yaml
id: SPEC-51
type: SPEC
labels: [post-mvp]
scheduled: ""
condition: normal
edges:
  - to: FR-16
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector がノードグラフを正常にパース済みである（SPEC-1 の正常系が先行している）。グラフに1件以上のノードが存在する。`--complexity` オプションが指定されている。
**入力/トリガ**: `spec-inspector --complexity` を実行する。
**期待動作**: 各ノードの in-degree（被参照数）・out-degree（参照数）・ハブ判定（in-degree または out-degree が閾値以上のノードをハブとして識別）を含むメトリクスレポートが stdout に出力される。レポートはノードを id 昇順でソートした行形式（`{node-id} | in={N} | out={N} | hub={yes/no}`）で表示され、exit code 0 で正常終了する。
**合格例**: ノード FR-1（被参照: SPEC-1, SPEC-2 の 2 件、参照先: SR-1 の 1 件）を含むグラフに `--complexity` を実行 → stdout に `FR-1 | in=2 | out=1 | hub=no`（in-degree 2、out-degree 1、閾値未満のためハブ判定 no）が含まれ、exit code 0 で終了する。
**違反例**: `--complexity` を実行したが stdout に何も出力されない・またはメトリクス行に `in=` / `out=` フィールドが欠落する → 期待動作を満たさない。
