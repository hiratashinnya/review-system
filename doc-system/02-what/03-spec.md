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
    ref_version: "0.3"
  - to: FND-14
    ref_version: "0.1"
  - to: FND-40
    ref_version: "0.1"
```
</details>

ノード埋め込みパースの正常系。期待動作は単一アサーション化のため SPEC-1-1〜1-3 へ分割した（階層は ID パターンで表現し親→子辺は持たない）。

---

## SPEC-1-1: 構造化ノード1件の生成（normal）

<details><summary>⬡ SPEC-1-1 · v0.1</summary>

```yaml
id: SPEC-1-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: FND-40
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `<details><summary>⬡ PREFIX-N` 形式の行が存在し、その直後に ```` ```yaml ```` ブロックがあり PyYAML safe_load でパース可能である。
**入力/トリガ**: 検証ツールが当該 in-graph ファイルを処理する。
**期待動作**: `⬡` マーカー直後の YAML ブロックがパース可能なとき、`id`・`type`・`labels`・`scheduled`・`edges` を持つ構造化ノードを 1 件生成する。
**例**: `doc-system/02-what/03-spec.md` 行15に `⬡ SPEC-1 · v0.3`、直後 YAML に `id: SPEC-1, type: SPEC` → ノード `{id:"SPEC-1", type:"SPEC", labels:[], scheduled:"", edges:[{to:"FR-1", ref_version:"0.3"}]}` を 1 件生成する。

---

## SPEC-1-2: マーカー PREFIX-N と YAML id の一致検証（normal）

<details><summary>⬡ SPEC-1-2 · v0.1</summary>

```yaml
id: SPEC-1-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: FND-40
    ref_version: "0.1"
```
</details>

**前提条件**: `⬡ PREFIX-N` マーカー直後の YAML ブロックから構造化ノードが 1 件生成済みである（SPEC-1-1 が先行）。
**入力/トリガ**: 検証ツールが当該ノードのマーカー行 `PREFIX-N` と YAML の `id` 値を照合する。
**期待動作**: マーカー行の `PREFIX-N` と YAML の `id` 値が一致するとき、当該ノードを ID 整合と判定する（不一致時は別 SPEC の責務）。
**例**: マーカー `⬡ SPEC-1 · v0.3` の `SPEC-1` と YAML `id: SPEC-1` → 一致 → ID 整合と判定する。

---

## SPEC-1-3: パース段違反なし → エラー出力なし（normal）

<details><summary>⬡ SPEC-1-3 · v0.1</summary>

```yaml
id: SPEC-1-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: FND-40
    ref_version: "0.1"
```
</details>

**前提条件**: `⬡ PREFIX-N` マーカー直後の YAML ブロックから構造化ノードが 1 件生成済みである（SPEC-1-1 が先行）。
**入力/トリガ**: 検証ツールが当該ノードに対し RULE-023〜027 を評価する。
**期待動作**: RULE-023〜027 の違反が 0 件のとき、当該ノード起因のエラー行を一切出力しない。
**例**: `id: SPEC-1, type: SPEC` の正常ノードで RULE-023〜027 違反なし → 標準出力に当該ノード起因の `ERROR|...` 行が現れない。

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
    ref_version: "0.3"
  - to: FND-14
    ref_version: "0.1"
  - to: FND-41
    ref_version: "0.1"
```
</details>

YAML 構文不正（RULE-023）時のパース失敗と fail-close 副作用の異常系。期待動作は単一アサーション化のため SPEC-2-1〜2-4 へ分割した（階層は ID パターンで表現し親→子辺は持たない）。

---

## SPEC-2-1: YAML 構文不正で RULE-023 ERROR を出力（error）

<details><summary>⬡ SPEC-2-1 · v0.1</summary>

```yaml
id: SPEC-2-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-2
    ref_version: "0.3"
  - to: FND-41
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカー行が存在し、その直後の YAML ブロック自体は存在する（マーカー欠落ではなく中身の構文不正のケース）。
**入力/トリガ**: その YAML ブロックが PyYAML safe_load で ScannerError または ParserError を発生させる（インデント不正・コロン欠如等）。
**期待動作**: YAML パースが例外を発生させたとき、`ERROR|{file}:{line}|RULE-023|(none)|YAML parse error: {例外メッセージ}` を 1 件出力する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に不正インデント → `ERROR|doc-system/02-what/01-fr.md:17|RULE-023|(none)|YAML parse error: mapping values are not allowed here` を出力する。

---

## SPEC-2-2: YAML 構文不正で当該ファイルのパースを中断（error）

<details><summary>⬡ SPEC-2-2 · v0.1</summary>

```yaml
id: SPEC-2-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-2
    ref_version: "0.3"
  - to: FND-41
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルの `⬡` マーカー直後の YAML ブロックが構文不正で、RULE-023 ERROR が出力された（SPEC-2-1 が先行）。
**入力/トリガ**: 検証ツールが当該ファイルの残りノードのパースを試みる。
**期待動作**: RULE-023 ERROR を検出したとき、当該ファイルのパースを中断する（fail-close・当該ファイルの後続ノードを生成しない）。
**例**: `doc-system/02-what/01-fr.md` 行17で RULE-023 ERROR → 同ファイル行30以降の `⬡` マーカーのノードを生成しない。

---

## SPEC-2-3: パース中断後は後続 RULE-024〜027 を発火させない（error）

<details><summary>⬡ SPEC-2-3 · v0.1</summary>

```yaml
id: SPEC-2-3
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-2
    ref_version: "0.3"
  - to: FND-41
    ref_version: "0.1"
```
</details>

**前提条件**: RULE-023 ERROR により当該ファイルのパースが中断された（SPEC-2-2 が先行）。
**入力/トリガ**: 検証ツールがパース段検証 RULE-024〜027 の評価フェーズに入る。
**期待動作**: 当該ファイルのパースが中断されたとき、当該ファイルに対し RULE-024〜027 を発火させない。
**例**: `doc-system/02-what/01-fr.md` が RULE-023 で中断 → 同ファイルに RULE-024（YAML ブロック欠如）・RULE-025/026/027 の違反行を出力しない。

---

## SPEC-2-4: 当該ファイル中断後も他 in-graph ファイルの処理を継続（error）

<details><summary>⬡ SPEC-2-4 · v0.1</summary>

```yaml
id: SPEC-2-4
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-2
    ref_version: "0.3"
  - to: FND-41
    ref_version: "0.1"
```
</details>

**前提条件**: 1 件の in-graph ファイルが RULE-023 でパース中断され、他に in-graph ファイルが 1 件以上存在する（SPEC-2-2 が先行）。
**入力/トリガ**: 検証ツールが残りの in-graph ファイルを走査する。
**期待動作**: 1 ファイルがパース中断されたとき、他 in-graph ファイルのパース・検証処理を継続する。
**例**: `doc-system/02-what/01-fr.md` が中断されても `doc-system/02-what/03-spec.md` のノードは通常どおりパース・検証される。

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
    ref_version: "0.2"
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
    ref_version: "0.2"
  - to: FND-42
    ref_version: "0.1"
```
</details>

ID 永続（リネームなし）と意味の担い手分離の正常系。期待動作は単一アサーション化のため SPEC-3-2-1〜3-2-2 へ分割した（階層は ID パターンで表現し親→子辺は持たない）。

---

## SPEC-3-2-1: 内容変更時も ID を永続させる（normal）

<details><summary>⬡ SPEC-3-2-1 · v0.1</summary>

```yaml
id: SPEC-3-2-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3-2
    ref_version: "0.1"
  - to: FND-42
    ref_version: "0.1"
```
</details>

**前提条件**: ID を持つノードが存在する。
**入力/トリガ**: ノードの見出し・本文・辺を変更する。
**期待動作**: ノードの見出し・本文・辺が変更されたとき、その ID を変更せず永続させる。
**例**: `SPEC-3-2` の本文を改訂しても `id: SPEC-3-2` は不変のまま追跡キーとして残る。

---

## SPEC-3-2-2: 意味は heading が担い ID は追跡キーに限定（normal）

<details><summary>⬡ SPEC-3-2-2 · v0.1</summary>

```yaml
id: SPEC-3-2-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3-2
    ref_version: "0.1"
  - to: FND-42
    ref_version: "0.1"
```
</details>

**前提条件**: ID と見出し（heading）を持つノードが存在する。
**入力/トリガ**: 読み手または検証ツールがノードの意味を解釈する。
**期待動作**: ノードの意味を解釈するとき、その意味は見出し（heading）が担い、ID は追跡キーとしてのみ機能する（ID 自体は意味を表さない）。
**例**: `SPEC-3-2` の意味は見出し「ID の永続（リネームなし）」が表し、`SPEC-3-2` という ID 文字列は意味を持たず追跡のみに使われる。

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
    ref_version: "0.2"
  - to: FND-43
    ref_version: "0.1"
```
</details>

階層 ID ノードの親存在判定の正常系。期待動作は単一アサーション化のため SPEC-3-3-1〜3-3-2 へ分割した（階層は ID パターンで表現し親→子辺は持たない）。

---

## SPEC-3-3-1: 階層は ID パターンから推論し親→子辺を要求しない（normal）

<details><summary>⬡ SPEC-3-3-1 · v0.1</summary>

```yaml
id: SPEC-3-3-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3-3
    ref_version: "0.1"
  - to: FND-43
    ref_version: "0.1"
```
</details>

**前提条件**: `I-1-1` のような子 ID を持つノードが存在する。
**入力/トリガ**: 検証ツールが階層関係を判定する。
**期待動作**: 階層関係を判定するとき、親→子の `decomposes` 辺を必須要求しない（階層は ID パターン `X-N` から推論する）。
**例**: `I-1-1` の親子関係は ID パターンから推論され、`I-1 → I-1-1` の明示辺がなくても違反としない。

---

## SPEC-3-3-2: 親ノードが存在すれば階層 ID を正常と判定（normal）

<details><summary>⬡ SPEC-3-3-2 · v0.1</summary>

```yaml
id: SPEC-3-3-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-3-3
    ref_version: "0.1"
  - to: FND-43
    ref_version: "0.1"
```
</details>

**前提条件**: `I-1-1` のような子 ID を持つノードが存在する。
**入力/トリガ**: 検証ツールが子 ID の親 `I-1` の存在を確認する。
**期待動作**: 子 ID の親ノード（`I-1`）が in-graph に存在するとき、当該階層 ID を正常（RULE-008 違反なし）と判定する。
**例**: `I-1-1` に対し親 `I-1` が in-graph に存在 → 孤児階層ではない → 正常と判定し RULE-008 を発火させない。

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
  - to: FND-44
    ref_version: "0.1"
```
</details>

**前提条件**: ノード集合がパースされている
**入力/トリガ**: 辺の `to` が存在しない ID を指す
**期待動作**: 存在しない ID 参照に関する検証は SPEC-6-1（RULE-007 ERROR 報告）・SPEC-6-2（always_error による抑制不可）に分割して規定する（本ノードは umbrella・テスタブルな単一アサーションは子に委譲）。

---

## SPEC-6-1: 存在しない ID 参照を RULE-007 ERROR 報告（error）

<details><summary>⬡ SPEC-6-1 · v0.1</summary>

```yaml
id: SPEC-6-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-6
    ref_version: "0.2"
  - to: FND-44
    ref_version: "0.1"
```
</details>

**前提条件**: ノード集合がパースされている
**入力/トリガ**: いずれかの辺の `to` が存在しない ID を指す
**期待動作**: 存在しない ID を指す辺があるとき、RULE-007 違反を ERROR として報告する。

---

## SPEC-6-2: RULE-007 は always_error で抑制不可（error）

<details><summary>⬡ SPEC-6-2 · v0.1</summary>

```yaml
id: SPEC-6-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-6
    ref_version: "0.2"
  - to: FND-44
    ref_version: "0.1"
```
</details>

**前提条件**: 存在しない ID を指す辺があり RULE-007 が発火する状態である
**入力/トリガ**: 当該ノードに `suppress: [RULE-007]`（または `scheduled` / 未達 `activate_stage`）が設定されている
**期待動作**: 抑制指定が設定されているとき、RULE-007 を抑制せず ERROR を報告する（always_error）。

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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
  - to: FND-45
    ref_version: "0.1"
```
</details>

**前提条件**: あるファイルの version の x または y が上昇する（z は不問）
**入力/トリガ**: 検証ツールが段階①を実行する
**期待動作**: ファイル x.y 上昇に伴う依存辺ドリフトの検証は SPEC-10-1（RULE-004 ERROR 検出）・SPEC-10-2（再反映の促し）に分割して規定する（本ノードは umbrella・status は持たず ref_version 更新で解消）。

---

## SPEC-10-1: ref_version 不一致を RULE-004 ERROR 検出（normal）

<details><summary>⬡ SPEC-10-1 · v0.1</summary>

```yaml
id: SPEC-10-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-10
    ref_version: "0.2"
  - to: FND-45
    ref_version: "0.1"
```
</details>

**前提条件**: あるファイルのノードバッジ x.y が上昇している（z は不問）
**入力/トリガ**: そのファイルのノードを参照する依存辺の `ref_version` が現バッジ x.y と一致しない
**期待動作**: `ref_version` がバッジ x.y と不一致のとき、RULE-004 違反を ERROR として検出・報告する。

---

## SPEC-10-2: ドリフト検出時に再反映を促すメッセージを出力（normal）

<details><summary>⬡ SPEC-10-2 · v0.1</summary>

```yaml
id: SPEC-10-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-10
    ref_version: "0.2"
  - to: FND-45
    ref_version: "0.1"
```
</details>

**前提条件**: RULE-004 ドリフトが検出されている（SPEC-10-1）
**入力/トリガ**: 検証ツールがドリフト違反の報告メッセージを生成する
**期待動作**: ドリフトを検出したとき、当該依存辺の `ref_version` を現バッジ x.y へ更新するよう促すメッセージを出力する。

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
  - to: FND-46
    ref_version: "0.1"
```
</details>

**前提条件**: 型が DD のノードがあり、反映完了時には著者が `DD→X` を削除し `X→DD` を追加する運用である（辺の削除・追加は著者の処置であり検証ツールの検証対象ではない）
**入力/トリガ**: DD の義務辺（`DD→X`）が存在する
**期待動作**: DD の義務辺 `DD→X` が残存するとき、RULE-001 違反を ERROR として報告する（型で判定・lifecycle パース不要）。

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
  - to: FND-18
    ref_version: "0.1"
```
</details>

**前提条件**: FR→SPEC→TD のグラフがパースされている
**入力/トリガ**: CLI を `--coverage` オプションで実行する
**期待動作**: FR ごとに condition 軸（normal/boundary/empty/failure/error）で SPEC と TD の充足状況を表にしたカバレッジレポートを出力する

---

## SPEC-14-1: カバレッジテーブルの出力フォーマット（normal）

<details><summary>⬡ SPEC-14-1 · v0.1</summary>

```yaml
id: SPEC-14-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-14
    ref_version: "0.2"
  - to: FND-18
    ref_version: "0.1"
  - to: FND-24
    ref_version: "0.1"
  - to: FND-47
    ref_version: "0.1"
```
</details>

**前提条件**: FR→SPEC→TD のグラフがパース済みで、SPEC-14 の `--coverage` 実行によりカバレッジテーブル本体が生成される文脈である。gap（カバレッジ欠如）の別セクション出力は SPEC-14 本体および RULE-017/018 の責務であり、本系では扱わない。
**入力/トリガ**: 検証ツールを `--coverage` オプションで実行する。
**期待動作**: カバレッジテーブル本体の出力仕様は SPEC-14-1-1（ヘッダ行）・SPEC-14-1-2（各 FR 行のセル値）・SPEC-14-1-3（FR-id 昇順ソート）・SPEC-14-1-4（終了コード 0）に分割して規定する（本ノードは umbrella）。
**例**: FR-1 に normal/empty/failure/error の SPEC があり boundary がない、FR-2 が次に存在する場合 → 各子 SPEC の規定に従い `FR-id | normal | boundary | empty | failure | error` のヘッダ行、`FR-1 | ✅ | ⬜ | ✅ | ✅ | ✅`、`FR-2 | ...` が FR-id 昇順で並び、終了コード 0。

---

## SPEC-14-1-1: カバレッジテーブルのヘッダ行出力（normal）

<details><summary>⬡ SPEC-14-1-1 · v0.1</summary>

```yaml
id: SPEC-14-1-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-14-1
    ref_version: "0.1"
  - to: FND-47
    ref_version: "0.1"
```
</details>

**前提条件**: 検証ツールがカバレッジテーブル本体を生成する文脈である（`--coverage` 実行）
**入力/トリガ**: カバレッジテーブルの 1 行目を出力する
**期待動作**: テーブル先頭に、ヘッダ行 `FR-id | normal | boundary | empty | failure | error`（` | ` 区切り 6 フィールド・列順 normal/boundary/empty/failure/error）を 1 行出力する。
**例**: 出力 1 行目 = `FR-id | normal | boundary | empty | failure | error`。

---

## SPEC-14-1-2: 各 FR 行のセル値出力（normal）

<details><summary>⬡ SPEC-14-1-2 · v0.1</summary>

```yaml
id: SPEC-14-1-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-14-1
    ref_version: "0.1"
  - to: FND-47
    ref_version: "0.1"
```
</details>

**前提条件**: ヘッダ行が出力済みで、各 FR を 1 行として明細を出力する文脈である
**入力/トリガ**: ある FR の condition 別 SPEC 充足状況を 1 行として出力する
**期待動作**: FR 1 件につき `{FR-id} | {セル} | {セル} | {セル} | {セル} | {セル}`（列順 normal/boundary/empty/failure/error）を 1 行出力し、各セルは当該 FR にその condition の SPEC が存在すれば `✅`、不在なら `⬜` とする。
**例**: FR-1 に normal/empty/failure/error の SPEC があり boundary がない場合 → `FR-1 | ✅ | ⬜ | ✅ | ✅ | ✅`。

---

## SPEC-14-1-3: 明細行を FR-id 昇順でソート出力（normal）

<details><summary>⬡ SPEC-14-1-3 · v0.1</summary>

```yaml
id: SPEC-14-1-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-14-1
    ref_version: "0.1"
  - to: FND-47
    ref_version: "0.1"
```
</details>

**前提条件**: 全 FR の明細行が生成されている（SPEC-14-1-2）
**入力/トリガ**: 明細行群を並べて出力する
**期待動作**: 明細行を FR-id の数値部（接頭辞を除いた数値）昇順でソートして出力する。
**例**: FR-1 行の次に FR-2 行が並ぶ（id 昇順）。

---

## SPEC-14-1-4: 正常出力時の終了コード 0（normal）

<details><summary>⬡ SPEC-14-1-4 · v0.1</summary>

```yaml
id: SPEC-14-1-4
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-14-1
    ref_version: "0.1"
  - to: FND-47
    ref_version: "0.1"
```
</details>

**前提条件**: カバレッジテーブルが正常に生成・出力された
**入力/トリガ**: 検証ツールが `--coverage` 実行を正常終了する
**期待動作**: カバレッジテーブルを正常出力したとき、終了コード 0 を返す。
**例**: 例外なくテーブル出力完了 → 終了コード 0。

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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
  - to: FND-48
    ref_version: "0.1"
```
</details>

発火ステージ未達のルールがサイレントになる挙動を、評価スキップ（SPEC-21-1-1）と非報告（SPEC-21-1-2）の単一アサーションに分割する。SPEC-21-1-1〜2 を参照。

---

## SPEC-21-1-1: 発火ステージ未達のルールは評価をスキップ（normal）

<details><summary>⬡ SPEC-21-1-1 · v0.1</summary>

```yaml
id: SPEC-21-1-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21-1
    ref_version: "0.1"
```
</details>

**前提条件**: ルール R の発火ステージ（`activate_stage`/`rule_activation`）が定義されている
**入力/トリガ**: `index(current_stage) < index(R の発火ステージ)`
**期待動作**: `index(current_stage) < index(R の発火ステージ)` のとき、R の評価をスキップする
**例**: current_stage=requirements・R の発火ステージ=verification のとき、R は評価対象から除外される

---

## SPEC-21-1-2: 発火ステージ未達のルールは違反を報告しない（normal）

<details><summary>⬡ SPEC-21-1-2 · v0.1</summary>

```yaml
id: SPEC-21-1-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21-1
    ref_version: "0.1"
```
</details>

**前提条件**: ルール R の発火ステージが定義され、`index(current_stage) < index(R の発火ステージ)` で R がスキップされている
**入力/トリガ**: スキップされた R に該当する違反候補が存在する
**期待動作**: スキップされた R の違反候補が存在するとき、その違反を報告しない（出力行を生成しない）
**例**: 発火ステージ未達の R が論理的に違反していても、`{SEVERITY}|...|{RULE}|...` 行は出力されない

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
  - to: FND-49
    ref_version: "0.1"
```
</details>

発火ステージ到達でルールが発火する挙動を、元の深刻度での評価（SPEC-21-2-1）と違反報告（SPEC-21-2-2）の単一アサーションに分割する。SPEC-21-2-1〜2 を参照。

---

## SPEC-21-2-1: 発火ステージ到達でルールを元の深刻度で評価（normal）

<details><summary>⬡ SPEC-21-2-1 · v0.1</summary>

```yaml
id: SPEC-21-2-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21-2
    ref_version: "0.1"
```
</details>

**前提条件**: ルール R の発火ステージが定義されている
**入力/トリガ**: `index(current_stage) >= index(R の発火ステージ)`
**期待動作**: `index(current_stage) >= index(R の発火ステージ)` のとき、R を config 定義の元の深刻度で評価する
**例**: R の severity=WARNING・current_stage が発火ステージ以上のとき、R は WARNING として評価される（降格・昇格しない）

---

## SPEC-21-2-2: 発火したルールの違反を報告（normal）

<details><summary>⬡ SPEC-21-2-2 · v0.1</summary>

```yaml
id: SPEC-21-2-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-21-2
    ref_version: "0.1"
```
</details>

**前提条件**: ルール R が発火ステージに到達し、元の深刻度で評価されている
**入力/トリガ**: 評価された R に該当する違反が存在する
**期待動作**: 発火した R に違反が存在するとき、その違反を `{SEVERITY}|{file}:{line}|{RULE-NNN}|{node-id}|{message}` 形式で報告する
**例**: R=RULE-004 が発火し対象ノードがドリフトしているとき、`WARNING|...|RULE-004|...` 行が1件出力される

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
  - to: FND-50
    ref_version: "0.1"
```
</details>

`always_error` 登録ルールが発火ステージ前・抑制有無に関わらず ERROR を報告する挙動を、RULE-007（SPEC-21-3-1）と RULE-005（SPEC-21-3-2）の単一目的語に分割する。「抑制設定を無視」は条件（always_error 登録ルールは抑制・発火ステージに関わらず）として各子に内包する。SPEC-21-3-1〜2 を参照。

---

## SPEC-21-3-1: always_error の RULE-007 は発火ステージ前でも ERROR 報告（error）

<details><summary>⬡ SPEC-21-3-1 · v0.1</summary>

```yaml
id: SPEC-21-3-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-21-3
    ref_version: "0.1"
```
</details>

**前提条件**: `always_error` に RULE-007 が登録されている（発火ステージ・suppress の状態に関わらず常に発火）
**入力/トリガ**: 存在しない ID を参照する辺が存在する
**期待動作**: 存在しない ID 参照が存在するとき、RULE-007 ERROR を報告する（always_error のため発火ステージ未達・suppress 指定でも抑制されない）
**例**: current_stage=requirements・`suppress: [RULE-007]` 指定でも、dangling 辺は `ERROR|...|RULE-007|...` として報告される

---

## SPEC-21-3-2: always_error の RULE-005 は発火ステージ前でも ERROR 報告（error）

<details><summary>⬡ SPEC-21-3-2 · v0.1</summary>

```yaml
id: SPEC-21-3-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-21-3
    ref_version: "0.1"
```
</details>

**前提条件**: `always_error` に RULE-005 が登録されている（発火ステージ・suppress の状態に関わらず常に発火）
**入力/トリガ**: 完全孤立ノード（辺を1本も持たないノード）が存在する
**期待動作**: 完全孤立ノードが存在するとき、RULE-005 ERROR を報告する（always_error のため発火ステージ未達・suppress 指定でも抑制されない）
**例**: current_stage=requirements・`suppress: [RULE-005]` 指定でも、孤立ノードは `ERROR|...|RULE-005|...` として報告される

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
  - to: FND-51
    ref_version: "0.1"
```
</details>

`current_stage` が `stages` に未定義のときのフェイルセーフ挙動を、設定エラー報告（SPEC-21-4-1）・ステージ判定スキップ（SPEC-21-4-2）・全ルール元深刻度評価（SPEC-21-4-3）の単一アサーションに分割する。SPEC-21-4-1〜3 を参照。

---

## SPEC-21-4-1: current_stage 未定義でツール設定エラーを報告（failure）

<details><summary>⬡ SPEC-21-4-1 · v0.1</summary>

```yaml
id: SPEC-21-4-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-21-4
    ref_version: "0.1"
```
</details>

**前提条件**: `config.yaml` に `current_stage` が設定されている
**入力/トリガ**: `stages` リストに `current_stage` 値が存在しない
**期待動作**: `current_stage` 値が `stages` に存在しないとき、ツール設定エラーを報告する
**例**: current_stage=`reqirements`（誤記）が stages に無いとき、設定エラー1件が出力される

---

## SPEC-21-4-2: current_stage 未定義でステージ発火判定をスキップ（failure）

<details><summary>⬡ SPEC-21-4-2 · v0.1</summary>

```yaml
id: SPEC-21-4-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-21-4
    ref_version: "0.1"
```
</details>

**前提条件**: `config.yaml` に `current_stage` が設定され、その値が `stages` に存在しない
**入力/トリガ**: ステージ発火判定（`index(current_stage)` の比較）を要求される
**期待動作**: `current_stage` 値が `stages` に存在しないとき、ステージ発火判定（index 比較）をスキップする
**例**: index(current_stage) が解決できないため、発火ステージとの大小比較は実行されない

---

## SPEC-21-4-3: current_stage 未定義時は全ルールを元の深刻度で評価（failure）

<details><summary>⬡ SPEC-21-4-3 · v0.1</summary>

```yaml
id: SPEC-21-4-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-21-4
    ref_version: "0.1"
```
</details>

**前提条件**: `current_stage` が `stages` に存在せず、ステージ発火判定がスキップされている
**入力/トリガ**: 全ルールの評価フェーズに入る
**期待動作**: ステージ発火判定がスキップされたとき、全ルールを元の深刻度で評価する（フェイルオープンせず沈黙させない）
**例**: 発火ステージ未達のルールも含め、全ルールが config 定義の深刻度で評価・報告される

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

## SPEC-23-1: RULE-007/005 を suppress に含めても抑制不可（error）

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
  - to: FND-52
    ref_version: "0.1"
```
</details>

**前提条件**: suppress 機構が動作している
**入力/トリガ**: ノードの `suppress` リストに always_error な RULE が含まれる
**期待動作**: SPEC-23-1-1〜SPEC-23-1-2 を参照（RULE-007／RULE-005 を suppress に含めても抑制せず常に ERROR 報告する各アサーション）。

---

## SPEC-23-1-1: suppress に RULE-007 を含めても ERROR 報告（error）

<details><summary>⬡ SPEC-23-1-1 · v0.1</summary>

```yaml
id: SPEC-23-1-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-23-1
    ref_version: "0.1"
```
</details>

**前提条件**: suppress 機構が動作しており、存在しない ID 参照を含むノードがある
**入力/トリガ**: ノードの `suppress` リストに RULE-007 が含まれる
**期待動作**: suppress に RULE-007 が含まれるとき、RULE-007 の ERROR を報告する（always_error のため抑制不可）。

---

## SPEC-23-1-2: suppress に RULE-005 を含めても ERROR 報告（error）

<details><summary>⬡ SPEC-23-1-2 · v0.1</summary>

```yaml
id: SPEC-23-1-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-23-1
    ref_version: "0.1"
```
</details>

**前提条件**: suppress 機構が動作しており、存在しない ID 参照を含むノードがある
**入力/トリガ**: ノードの `suppress` リストに RULE-005 が含まれる
**期待動作**: suppress に RULE-005 が含まれるとき、RULE-005 の ERROR を報告する（always_error のため抑制不可）。

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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.2"
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
    ref_version: "0.4"
  - to: FND-14
    ref_version: "0.1"
  - to: FND-53
    ref_version: "0.1"
```
</details>

**前提条件**: `templates/<layer>/<type>.md` が存在する（layer ∈ {requirements, analysis, design, verification}、type はその層の型名。例 `templates/requirements/SPEC.md`）。
**入力/トリガ**: 著者がテンプレートを複製してノード著作を開始する。
**期待動作**: SPEC-26-1〜SPEC-26-4 を参照（テンプレ完備性と複製時の RULE-025／026／027 各不発火）。

---

## SPEC-26-1: テンプレートが必須フィールドを全て含む（normal）

<details><summary>⬡ SPEC-26-1 · v0.1</summary>

```yaml
id: SPEC-26-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-26
    ref_version: "0.3"
```
</details>

**前提条件**: `templates/<layer>/<type>.md` が存在する（例 `templates/requirements/SPEC.md`）。
**入力/トリガ**: 著者がテンプレートを複製してノード著作を開始する。
**期待動作**: テンプレートを検査するとき、`id:`（プレースホルダ）・`type:`（型名）・`labels: []`・`scheduled: ""`・`edges:`（≥1エントリ・各エントリに `to:` と `ref_version:`）・本文4項目（`**前提条件**:`／`**入力/トリガ**:`／`**期待動作**:`／`**例**:`）を全て含むことを確認する。
**例**: `templates/requirements/SPEC.md` を複製すると `id: SPEC-XXX`・`type: SPEC`・`edges: [{to: FR-XX, ref_version: "0.0"}]`・本文4項目が存在する。

---

## SPEC-26-2: 複製直後に RULE-025 が不発火（normal）

<details><summary>⬡ SPEC-26-2 · v0.1</summary>

```yaml
id: SPEC-26-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-26
    ref_version: "0.3"
```
</details>

**前提条件**: テンプレート `templates/<layer>/<type>.md` が必須フィールドを備えている。
**入力/トリガ**: テンプレートを複製した初期状態のノードを検証する。
**期待動作**: 複製直後のノードを検証するとき、RULE-025 を発火させない。
**例**: `templates/requirements/SPEC.md` を複製した直後のノードに対し RULE-025 が発火しない。

---

## SPEC-26-3: 複製直後に RULE-026 が不発火（normal）

<details><summary>⬡ SPEC-26-3 · v0.1</summary>

```yaml
id: SPEC-26-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-26
    ref_version: "0.3"
```
</details>

**前提条件**: テンプレート `templates/<layer>/<type>.md` が必須フィールドを備えている。
**入力/トリガ**: テンプレートを複製した初期状態のノードを検証する。
**期待動作**: 複製直後のノードを検証するとき、RULE-026 を発火させない。
**例**: `templates/requirements/SPEC.md` を複製した直後のノードに対し RULE-026 が発火しない。

---

## SPEC-26-4: 複製直後に RULE-027 が不発火（normal）

<details><summary>⬡ SPEC-26-4 · v0.1</summary>

```yaml
id: SPEC-26-4
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-26
    ref_version: "0.3"
```
</details>

**前提条件**: テンプレート `templates/<layer>/<type>.md` が必須フィールドを備えている。
**入力/トリガ**: テンプレートを複製した初期状態のノードを検証する。
**期待動作**: 複製直後のノードを検証するとき、RULE-027 を発火させない。
**例**: `templates/requirements/SPEC.md` を複製した直後のノードに対し RULE-027 が発火しない。

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
    ref_version: "0.1"
  - to: FND-14
    ref_version: "0.1"
  - to: FND-54
    ref_version: "0.1"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義（例 `requirements-author.md`）が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: SPEC-27-1〜SPEC-27-5 を参照（外部参照なしに提供する type 値・id PREFIX・必須辺方向・本文4項目・RULE チェックリストの各構成要素）。

---

## SPEC-27-1: エージェントが外部参照なしに type 値を提供（normal）

<details><summary>⬡ SPEC-27-1 · v0.1</summary>

```yaml
id: SPEC-27-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: エージェントを呼び出すとき、外部ファイル参照なしに対象型の `type` 値を提供する。
**例**: `requirements-author` に FR 著作を依頼すると `type: FR` の指示が定義に内包される。

---

## SPEC-27-2: エージェントが外部参照なしに id PREFIX パターンを提供（normal）

<details><summary>⬡ SPEC-27-2 · v0.1</summary>

```yaml
id: SPEC-27-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: エージェントを呼び出すとき、外部ファイル参照なしに対象型の `id` PREFIX パターンを提供する。
**例**: `requirements-author` に FR 著作を依頼すると `id: FR-*` の PREFIX 指示が定義に内包される。

---

## SPEC-27-3: エージェントが外部参照なしに必須辺方向を提供（normal）

<details><summary>⬡ SPEC-27-3 · v0.1</summary>

```yaml
id: SPEC-27-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: エージェントを呼び出すとき、外部ファイル参照なしに対象型の必須辺方向（`to` 先の型と方向）を提供する。
**例**: `requirements-author` に FR 著作を依頼すると `edges[].to: SR-*`（SR 辺必須）の指示が定義に内包される。

---

## SPEC-27-4: エージェントが外部参照なしに本文4項目フォーマットを提供（normal）

<details><summary>⬡ SPEC-27-4 · v0.1</summary>

```yaml
id: SPEC-27-4
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: エージェントを呼び出すとき、外部ファイル参照なしに本文4項目フォーマットを提供する。
**例**: `requirements-author` に FR 著作を依頼すると4項目本文の指示が定義に内包される。

---

## SPEC-27-5: エージェントが外部参照なしに RULE チェックリストを提供（normal）

<details><summary>⬡ SPEC-27-5 · v0.1</summary>

```yaml
id: SPEC-27-5
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在する。
**入力/トリガ**: 著者が型別著作エージェントを呼び出してノード著作を実行する。
**期待動作**: エージェントを呼び出すとき、外部ファイル参照なしに対象型の RULE チェックリストを提供する。
**例**: `requirements-author` に FR 著作を依頼すると対象 RULE のチェックリストが定義に内包される。

---

## SPEC-28: SRC の @id realizes 検証（normal・post-mvp）

<details><summary>⬡ SPEC-28 · v0.3</summary>

```yaml
id: SPEC-28
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: FR-12
    ref_version: "0.2"
  - to: FND-78
    ref_version: "0.1"
  - to: FND-55
    ref_version: "0.1"
```
</details>

**前提条件**: ソースに `@id` アノテーションがあり、設計層に DM/PORT/ORC ノードがある
**入力/トリガ**: 段階④の検証を実行する
**期待動作**: SPEC-28-1〜SPEC-28-2 を参照（`@id`→DM/PORT/ORC の realizes 辺照合による設計漏れ検出・紐づけ漏れ検出）。

---

## SPEC-28-1: realizes 照合で設計漏れを検出（normal・post-mvp）

<details><summary>⬡ SPEC-28-1 · v0.1</summary>

```yaml
id: SPEC-28-1
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-28
    ref_version: "0.3"
```
</details>

**前提条件**: ソースに `@id` アノテーションがあり、設計層に DM/PORT/ORC ノードがある
**入力/トリガ**: 段階④の検証で `@id`→DM/PORT/ORC の realizes 辺を照合する
**期待動作**: realizes 辺を照合するとき、実装あり・設計なしの設計漏れを検出する。

---

## SPEC-28-2: realizes 照合で紐づけ漏れを検出（normal・post-mvp）

<details><summary>⬡ SPEC-28-2 · v0.1</summary>

```yaml
id: SPEC-28-2
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-28
    ref_version: "0.3"
```
</details>

**前提条件**: ソースに `@id` アノテーションがあり、設計層に DM/PORT/ORC ノードがある
**入力/トリガ**: 段階④の検証で `@id`→DM/PORT/ORC の realizes 辺を照合する
**期待動作**: realizes 辺を照合するとき、設計あり・realizes なしの紐づけ漏れを検出する。

---

## SPEC-29: グラフ網羅性点検の正常系（normal・アンブレラ）

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
  - to: FND-56
    ref_version: "0.1"
```
</details>

**概要**: グラフ網羅性点検の正常系。検証アサーションは子 SPEC-29-1〜2 を参照（1アサーション1SPEC・FND-56 で分割）。

---

## SPEC-29-1: 孤立・必須辺欠如のゼロ件通過（normal）

<details><summary>⬡ SPEC-29-1 · v0.1</summary>

```yaml
id: SPEC-29-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-29
    ref_version: "0.1"
```
</details>

**前提条件**: 全 I/O/D/P/E ノードが適切な接続を持つ（O→P・O→ACTOR・D→P・E→ACTOR・P→I/D/E の各依存辺、および I←P・D←P・E←P の被依存辺が揃っている）
**入力/トリガ**: 検証ツールがグラフ網羅性点検（P-3-1）を実行する
**期待動作**: 孤立ノード（RULE-005）と必須辺欠如（RULE-006 の analysis 段接続）がいずれも0件であるとき、違反0件として点検を通過させる

---

## SPEC-29-2: 価値経路到達の充足判定（normal）

<details><summary>⬡ SPEC-29-2 · v0.1</summary>

```yaml
id: SPEC-29-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-29
    ref_version: "0.1"
```
</details>

**前提条件**: 全 I/O/D/P/E ノードが適切な接続を持つ（O→P・O→ACTOR・D→P・E→ACTOR・P→I/D/E の各依存辺、および I←P・D←P・E←P の被依存辺が揃っている）
**入力/トリガ**: 検証ツールがグラフ網羅性点検（P-3-1）を実行する
**期待動作**: 全ノードが VAL まで到達可能であるとき、グラフが価値経路を完全に満たすと判定する（分析層接続の充足は SPEC-29-1 が担保）

---

## SPEC-30: 分析ノードの接続漏れ検出（failure・アンブレラ）

<details><summary>⬡ SPEC-30 · v0.2</summary>

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
  - to: FND-57
    ref_version: "0.1"
  - to: FND-87
    ref_version: "0.1"
```
</details>

**概要**: 分析ノードの接続漏れ検出（SPEC-8 の一般則における分析層の特殊ケース）。検証アサーションは子 SPEC-30-1〜3 を参照（接続漏れ3種を1アサーション1SPEC に分割・FND-57）。なお D（内部データ）の接続漏れ（D→P・P→D 欠如）は一般則 SPEC-8（RULE-006 全般）でカバーされ、本傘 SPEC-30 はアクタに面する価値経路の名前付き漏れ3種（未駆動出力 O→P・未定義反応 E←P・未消費入力 I←P）のみを列挙する（D は内部データのため本傘の対象外）。

---

## SPEC-30-1: 未駆動出力（O→P 欠如）の検出（failure）

<details><summary>⬡ SPEC-30-1 · v0.1</summary>

```yaml
id: SPEC-30-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-30
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に分析層ノード（O）が存在する
**入力/トリガ**: P-3-1 がグラフ網羅性を確認する際に、O に P への依存辺（O→P）がないノードを検出する
**期待動作**: O→P 欠如のノードを検出したとき、未駆動出力として RULE-006 の config `activate_stage: analysis` 行の severity で報告する

---

## SPEC-30-2: 未定義反応イベント（E←P 欠如）の検出（failure）

<details><summary>⬡ SPEC-30-2 · v0.1</summary>

```yaml
id: SPEC-30-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-30
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に分析層ノード（E）が存在する
**入力/トリガ**: P-3-1 がグラフ網羅性を確認する際に、E に P からの被依存辺（E←P）がないノードを検出する
**期待動作**: E←P 欠如のノードを検出したとき、未定義反応イベントとして RULE-006 の config `activate_stage: analysis` 行の severity で報告する

---

## SPEC-30-3: 未消費入力（I←P 欠如）の検出（failure）

<details><summary>⬡ SPEC-30-3 · v0.1</summary>

```yaml
id: SPEC-30-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-30
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に分析層ノード（I）が存在する
**入力/トリガ**: P-3-1 がグラフ網羅性を確認する際に、I に P からの被依存辺（I←P）がないノードを検出する
**期待動作**: I←P 欠如のノードを検出したとき、未消費入力として RULE-006 の config `activate_stage: analysis` 行の severity で報告する

---

## SPEC-31: trace_scope による in-graph 0 件（empty・アンブレラ）

<details><summary>⬡ SPEC-31 · v0.1</summary>

```yaml
id: SPEC-31
type: SPEC
labels: []
scheduled: ""
condition: empty
edges:
  - to: FR-1
    ref_version: "0.3"
  - to: FND-13
    ref_version: "0.1"
  - to: FND-58
    ref_version: "0.1"
```
</details>

**概要**: trace_scope の結果 in-graph が0件のときの振る舞い。検証アサーションは子 SPEC-31-1〜4 を参照（違反0件報告・ノード0件報告・終了コード・ルールスキップを1アサーション1SPEC に分割・FND-58）。
**例**: `trace_scope.include: ["doc-system/**/*.md"]` かつ `exclude: ["doc-system/**/*.md"]` → in-graph ファイル0件・ノード0件・違反0件・終了コード 0。

---

## SPEC-31-1: in-graph 0 件で違反0件を報告（empty）

<details><summary>⬡ SPEC-31-1 · v0.1</summary>

```yaml
id: SPEC-31-1
type: SPEC
labels: []
scheduled: ""
condition: empty
edges:
  - to: SPEC-31
    ref_version: "0.1"
```
</details>

**前提条件**: `config.yaml` の `trace_scope` 設定の結果、in-graph ファイルが0件になる。
**入力/トリガ**: 検証ツールを実行する。
**期待動作**: in-graph ファイルが0件であるとき、違反0件を報告する。

---

## SPEC-31-4: in-graph 0 件でノード0件を報告（empty）

<details><summary>⬡ SPEC-31-4 · v0.1</summary>

```yaml
id: SPEC-31-4
type: SPEC
labels: []
scheduled: ""
condition: empty
edges:
  - to: SPEC-31
    ref_version: "0.1"
```
</details>

**前提条件**: `config.yaml` の `trace_scope` 設定の結果、in-graph ファイルが0件になる。
**入力/トリガ**: 検証ツールを実行する。
**期待動作**: in-graph ファイルが0件であるとき、ノード0件を報告する。

---

## SPEC-31-2: in-graph 0 件で終了コード 0（empty）

<details><summary>⬡ SPEC-31-2 · v0.1</summary>

```yaml
id: SPEC-31-2
type: SPEC
labels: []
scheduled: ""
condition: empty
edges:
  - to: SPEC-31
    ref_version: "0.1"
```
</details>

**前提条件**: `config.yaml` の `trace_scope` 設定の結果、in-graph ファイルが0件になる。
**入力/トリガ**: 検証ツールを実行する。
**期待動作**: in-graph ファイルが0件であるとき、終了コード 0 で終了する。

---

## SPEC-31-3: in-graph 0 件で RULE 評価を全スキップ（empty）

<details><summary>⬡ SPEC-31-3 · v0.1</summary>

```yaml
id: SPEC-31-3
type: SPEC
labels: []
scheduled: ""
condition: empty
edges:
  - to: SPEC-31
    ref_version: "0.1"
```
</details>

**前提条件**: `config.yaml` の `trace_scope` 設定の結果、in-graph ファイルが0件になる。
**入力/トリガ**: 検証ツールを実行する。
**期待動作**: in-graph ファイルが0件であるとき、RULE-005〜027 の評価を全てスキップする。

---

## SPEC-32: ⬡ マーカー直後に YAML ブロックなし（error・RULE-024・アンブレラ）

<details><summary>⬡ SPEC-32 · v0.1</summary>

```yaml
id: SPEC-32
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.3"
  - to: FND-59
    ref_version: "0.1"
```
</details>

**概要**: `⬡` マーカー直後に YAML ブロックがない場合のパース異常（RULE-024）。検証アサーションは子 SPEC-32-1〜2 を参照（出力と中断を1アサーション1SPEC に分割・FND-59）。
**例**: `doc-system/03-analysis/02-io.md` 行20に `⬡ I-1 · v0.3`、行21が `## I-1-1:` → `ERROR|doc-system/03-analysis/02-io.md:20|RULE-024|(none)|⬡ marker at line 20 has no YAML block following`。

---

## SPEC-32-1: ⬡ マーカー直後 YAML 欠如で RULE-024 ERROR 出力（error）

<details><summary>⬡ SPEC-32-1 · v0.1</summary>

```yaml
id: SPEC-32-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-32
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカー行が1件以上存在する。
**入力/トリガ**: `⬡` マーカー行の直後行が ```` ```yaml ```` ブロック開始行でない（heading／空行＋heading／別の `⬡` マーカーが直後に来る）。
**期待動作**: `⬡` マーカー直後に YAML ブロックがないとき、`ERROR|{file}:{line}|RULE-024|(none)|⬡ marker at line N has no YAML block following` を出力する。

---

## SPEC-32-2: ⬡ マーカー直後 YAML 欠如で当該ファイルのパース中断（error）

<details><summary>⬡ SPEC-32-2 · v0.1</summary>

```yaml
id: SPEC-32-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-32
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカー行が1件以上存在する。
**入力/トリガ**: `⬡` マーカー行の直後行が ```` ```yaml ```` ブロック開始行でない（heading／空行＋heading／別の `⬡` マーカーが直後に来る）。
**期待動作**: `⬡` マーカー直後に YAML ブロックがないとき、当該ファイルのパースを中断する（fail-close）。

---

## SPEC-33: id フィールド欠如・空（error・RULE-025・アンブレラ）

<details><summary>⬡ SPEC-33 · v0.1</summary>

```yaml
id: SPEC-33
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.3"
  - to: FND-60
    ref_version: "0.1"
```
</details>

**概要**: in-graph ノードの `id` フィールド欠如・空（RULE-025）に対する ERROR 出力と後続 RULE 中断を、子 SPEC-33-1〜2 で個別に検証する（傘ノード・非テスタブル）。

---

## SPEC-33-1: id 欠如時に RULE-025 ERROR を出力（error）

<details><summary>⬡ SPEC-33-1 · v0.1</summary>

```yaml
id: SPEC-33-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-33
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと直後の YAML ブロックが存在し、YAML は safe_load でパース可能である。
**入力/トリガ**: YAML ブロックに `id` キーが存在しない、または値が空文字列（`id: ""`）である。
**期待動作**: `id` キーが欠如・空のとき、`ERROR|{file}:{line}|RULE-025|(none)|id field missing or empty` を出力する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に id キーなし → `ERROR|doc-system/02-what/01-fr.md:17|RULE-025|(none)|id field missing or empty`。

---

## SPEC-33-2: id 欠如時に当該ノードの後続 RULE 評価を中断（error）

<details><summary>⬡ SPEC-33-2 · v0.1</summary>

```yaml
id: SPEC-33-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-33
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと直後の YAML ブロックが存在し、YAML は safe_load でパース可能である。
**入力/トリガ**: YAML ブロックに `id` キーが存在しない、または値が空文字列（`id: ""`）である。
**期待動作**: `id` キーが欠如・空のとき、当該ノードの後続 RULE 評価を中断する（他ファイル・他ノードの評価は継続する）。
**例**: id キーなしのノードでは RULE-025 出力後、当該ノードに対する RULE-026 以降を評価しない。次ノードの評価は継続する。

---

## SPEC-34: type フィールド欠如・空（error・RULE-026・アンブレラ）

<details><summary>⬡ SPEC-34 · v0.1</summary>

```yaml
id: SPEC-34
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: FR-1
    ref_version: "0.3"
  - to: FND-61
    ref_version: "0.1"
```
</details>

**概要**: in-graph ノードの `type` フィールド欠如・空（RULE-026）に対する ERROR 出力と後続 RULE 中断を、子 SPEC-34-1〜2 で個別に検証する（傘ノード・非テスタブル）。

---

## SPEC-34-1: type 欠如時に RULE-026 ERROR を出力（error）

<details><summary>⬡ SPEC-34-1 · v0.1</summary>

```yaml
id: SPEC-34-1
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-34
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと YAML ブロックが存在し、YAML パース可能で `id` キーは存在する。
**入力/トリガ**: YAML ブロックに `type` キーが存在しない、または値が空文字列である。
**期待動作**: `type` キーが欠如・空のとき、`ERROR|{file}:{line}|RULE-026|{id}|type field missing or empty` を出力する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に type なし・id は `FR-1` → `ERROR|doc-system/02-what/01-fr.md:17|RULE-026|FR-1|type field missing or empty`。

---

## SPEC-34-2: type 欠如時に当該ノードの後続 RULE 評価を中断（error）

<details><summary>⬡ SPEC-34-2 · v0.1</summary>

```yaml
id: SPEC-34-2
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-34
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに `⬡` マーカーと YAML ブロックが存在し、YAML パース可能で `id` キーは存在する。
**入力/トリガ**: YAML ブロックに `type` キーが存在しない、または値が空文字列である。
**期待動作**: `type` キーが欠如・空のとき、当該ノードの後続 RULE 評価を中断する（他ファイル・他ノードの評価は継続する）。
**例**: type キーなしのノードでは RULE-026 出力後、当該ノードに対する後続 RULE を評価しない。次ノードの評価は継続する。

---

## SPEC-35: edge に ref_version 欠如（failure・RULE-027・アンブレラ）

<details><summary>⬡ SPEC-35 · v0.1</summary>

```yaml
id: SPEC-35
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-1
    ref_version: "0.3"
  - to: FND-62
    ref_version: "0.1"
```
</details>

**概要**: `edges` エントリの `ref_version` 欠如（RULE-027）に対する ERROR 出力と後続 RULE 中断を、子 SPEC-35-1〜2 で個別に検証する（傘ノード・非テスタブル）。

---

## SPEC-35-1: edge の ref_version 欠如時に RULE-027 ERROR を出力（failure）

<details><summary>⬡ SPEC-35-1 · v0.1</summary>

```yaml
id: SPEC-35-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-35
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに YAML ブロックが存在し、`id`・`type` は存在する。`edges` リストに1件以上のエントリがある。
**入力/トリガ**: `edges` の任意のエントリに `ref_version` キーが存在しない。
**期待動作**: `edges` エントリに `ref_version` が欠如するとき、`ERROR|{file}:{line}|RULE-027|{id}|edge to {target_id}: ref_version missing` を出力する。
**例**: SPEC-1 ノードの edges に `{to: FR-1}`（ref_version なし）→ `ERROR|doc-system/02-what/03-spec.md:22|RULE-027|SPEC-1|edge to FR-1: ref_version missing`。

---

## SPEC-35-2: edge の ref_version 欠如時に当該ノードの後続 RULE 評価を中断（failure）

<details><summary>⬡ SPEC-35-2 · v0.1</summary>

```yaml
id: SPEC-35-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-35
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルに YAML ブロックが存在し、`id`・`type` は存在する。`edges` リストに1件以上のエントリがある。
**入力/トリガ**: `edges` の任意のエントリに `ref_version` キーが存在しない。
**期待動作**: `edges` エントリに `ref_version` が欠如するとき、当該ノードの後続 RULE 評価を中断する（他ファイル・他ノードの評価は継続する）。
**例**: ref_version 欠如ノードでは RULE-027 出力後、当該ノードに対する後続 RULE を評価しない。次ノードの評価は継続する。

---

## SPEC-36: テンプレート由来の必須フィールド欠如（failure・アンブレラ）

<details><summary>⬡ SPEC-36 · v0.1</summary>

```yaml
id: SPEC-36
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-11
    ref_version: "0.4"
  - to: FND-63
    ref_version: "0.1"
```
</details>

**概要**: テンプレート由来で必須フィールドを欠くノードに対し、id 欠如時の RULE-025・type 欠如時の RULE-026 をそれぞれ子 SPEC-36-1〜2 で個別に検証する（傘ノード・非テスタブル）。

---

## SPEC-36-1: テンプレート由来 id 欠如時に RULE-025 ERROR を報告（failure）

<details><summary>⬡ SPEC-36-1 · v0.1</summary>

```yaml
id: SPEC-36-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-36
    ref_version: "0.1"
```
</details>

**前提条件**: テンプレート `templates/<layer>/<type>.md` の `id:` フィールドが削除されている、または空になっている。
**入力/トリガ**: 著者がその `id` 欠落テンプレートを複製してノードを著作し、検証ツールが当該ノードを処理する。
**期待動作**: テンプレート由来で `id` を欠くとき、RULE-025（id 欠如）の ERROR を報告する。
**例**: `templates/requirements/FR.md` の `id:` 行が削除 → 著者が複製して `doc-system/02-what/01-fr.md` 行14に著作 → `ERROR|doc-system/02-what/01-fr.md:14|RULE-025|(none)|id field missing or empty`。

---

## SPEC-36-2: テンプレート由来 type 欠如時に RULE-026 ERROR を報告（failure）

<details><summary>⬡ SPEC-36-2 · v0.1</summary>

```yaml
id: SPEC-36-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-36
    ref_version: "0.1"
```
</details>

**前提条件**: テンプレート `templates/<layer>/<type>.md` の `type:` フィールドが削除されている、または空になっている（`id:` は存在する）。
**入力/トリガ**: 著者がその `type` 欠落テンプレートを複製してノードを著作し、検証ツールが当該ノードを処理する。
**期待動作**: テンプレート由来で `type` を欠くとき、RULE-026（type 欠如）の ERROR を報告する。
**例**: `templates/requirements/FR.md` の `type:` 行が削除 → 著者が複製して `doc-system/02-what/01-fr.md` 行14に著作（id は `FR-1`）→ `ERROR|doc-system/02-what/01-fr.md:14|RULE-026|FR-1|type field missing or empty`。

---

## SPEC-38: 著作エージェント出力と reconciliation 転記（normal・アンブレラ）

<details><summary>⬡ SPEC-38 · v0.1</summary>

```yaml
id: SPEC-38
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-13
    ref_version: "0.1"
  - to: FND-64
    ref_version: "0.1"
```
</details>

**概要**: 著作エージェントの規約準拠 tmp 出力（SPEC-38-1）と reconciliation の本ファイル転記（SPEC-38-2）を、子 SPEC で個別に検証する（傘ノード・非テスタブル）。

---

## SPEC-38-1: 著作エージェントが規約準拠ノードを tmp 出力（normal）

<details><summary>⬡ SPEC-38-1 · v0.1</summary>

```yaml
id: SPEC-38-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-38
    ref_version: "0.1"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義（例 `requirements-author.md`）が存在し、著者が FR 著作を依頼する。
**入力/トリガ**: 著者が `requirements-author` エージェントに FR ノード1件の著作を依頼する。
**期待動作**: 著者が著作を依頼したとき、エージェントは `type: FR`・`id: FR-N`（連番）・`edges: [{to: SR-*, ref_version: "..."}]`・本文4項目を含むノードを `tmp/sprint-1/<parent-id>.md` に出力する。
**例**: `requirements-author` に「FR-13 著作」を依頼 → `tmp/sprint-1/fr-11-13-14.md` に `id: FR-13, type: FR, edges: [{to: SR-1, ref_version: "0.2"}]` ＋4項目本文が出力される。

---

## SPEC-38-2: reconciliation が tmp 出力を本ファイルに転記（normal）

<details><summary>⬡ SPEC-38-2 · v0.1</summary>

```yaml
id: SPEC-38-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-38
    ref_version: "0.1"
```
</details>

**前提条件**: 著作エージェントが規約準拠ノードを `tmp/sprint-1/<parent-id>.md` に出力済みで、検証エラーがない。
**入力/トリガ**: 著者が reconciliation エージェントに tmp 出力の反映を依頼する。
**期待動作**: 検証を通過した tmp 出力に対し、reconciliation は当該ノードを本ファイルに転記する。
**例**: `tmp/sprint-1/fr-11-13-14.md` の FR-13 ノードが検証通過 → reconciliation が `doc-system/02-what/01-fr.md` に当該ノードを転記する。

---

## SPEC-39: 著作出力の id 欠如検出時の reconciliation 挙動（failure・アンブレラ）

<details><summary>⬡ SPEC-39 · v0.1</summary>

```yaml
id: SPEC-39
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-13
    ref_version: "0.1"
  - to: FND-65
    ref_version: "0.1"
```
</details>

**概要**: 著作出力の id 欠如に対する reconciliation の検証エラー報告（SPEC-39-1）・具体メッセージ出力（SPEC-39-2）・転記中断（SPEC-39-3）を、子 SPEC で個別に検証する（傘ノード・非テスタブル）。

---

## SPEC-39-1: id 欠如 tmp 出力に reconciliation が検証エラーを報告（failure）

<details><summary>⬡ SPEC-39-1 · v0.1</summary>

```yaml
id: SPEC-39-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-39
    ref_version: "0.1"
```
</details>

**前提条件**: エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力済みである。
**入力/トリガ**: reconciliation が tmp ファイルを検証し、id フィールドの欠如を検出する。
**期待動作**: id 欠如を検出したとき、reconciliation は検証エラーを報告する。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → reconciliation が検証エラーを報告する。

---

## SPEC-39-2: id 欠如検出時に RULE-025 相当メッセージを出力（failure）

<details><summary>⬡ SPEC-39-2 · v0.1</summary>

```yaml
id: SPEC-39-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-39
    ref_version: "0.1"
```
</details>

**前提条件**: エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力済みで、reconciliation が検証フェーズで RULE-025 相当チェックを実施する。
**入力/トリガ**: reconciliation が tmp ファイルの id 欠如を検出する。
**期待動作**: id 欠如を検出したとき、reconciliation は `ERROR|{file}:{line}|RULE-025|(none)|id field missing or empty` を出力する。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → `ERROR|tmp/sprint-1/fr-11-13-14.md:5|RULE-025|(none)|id field missing or empty` を出力する。

---

## SPEC-39-3: id 欠如検出時に reconciliation が転記を中断（failure）

<details><summary>⬡ SPEC-39-3 · v0.1</summary>

```yaml
id: SPEC-39-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-39
    ref_version: "0.1"
```
</details>

**前提条件**: エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力済みである。
**入力/トリガ**: reconciliation が tmp ファイルの id 欠如を検出する。
**期待動作**: id 欠如を検出したとき、reconciliation は本ファイルへの転記を中断する（fail-close）。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → reconciliation が `doc-system/02-what/01-fr.md` への転記を中断する。

---

## SPEC-40: 伝搬編集支援の表示（normal・post-mvp・アンブレラ）

<details><summary>⬡ SPEC-40 · v0.2</summary>

```yaml
id: SPEC-40
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: FR-14
    ref_version: "0.1"
  - to: FND-78
    ref_version: "0.1"
  - to: FND-66
    ref_version: "0.1"
```
</details>

**概要**: 伝搬編集支援のドリフトノード一覧出力（SPEC-40-1）と各行の更新フォーマット表示（SPEC-40-2）を、子 SPEC で個別に検証する（傘ノード・非テスタブル）。

---

## SPEC-40-1: 伝搬時にドリフトノード一覧を表形式で出力（normal・post-mvp）

<details><summary>⬡ SPEC-40-1 · v0.1</summary>

```yaml
id: SPEC-40-1
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-40
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph ファイル A の version x.y が上昇し、1件以上のノード B が `to: A, ref_version: "旧 x.y"` の辺を持つ（RULE-004 ドリフト状態）。
**入力/トリガ**: 著者が `--propagate A` オプションで検証ツールを実行する。
**期待動作**: `--propagate A` を実行したとき、RULE-004 ドリフトが検出されたノード B の一覧を表形式で出力する。
**例**: `doc-system/03-analysis/02-io.md` の version が `0.5`→`0.6` に上昇 → ドリフトノード `P-1` を含む一覧を表形式で出力する。

---

## SPEC-40-2: ドリフト一覧の各行を更新フォーマットで表示（normal・post-mvp）

<details><summary>⬡ SPEC-40-2 · v0.1</summary>

```yaml
id: SPEC-40-2
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-40
    ref_version: "0.2"
```
</details>

**前提条件**: `--propagate A` 実行により RULE-004 ドリフトノード一覧が得られている。
**入力/トリガ**: 検証ツールがドリフト一覧の各行を整形して出力する。
**期待動作**: ドリフト一覧を表示するとき、各行を `{node-id} | {file}:{line} | ref_version: "{old}" → "{new}"` 形式で表示する。
**例**: `P-1 | doc-system/03-analysis/03-processes.md:26 | ref_version: "0.5" → "0.6"` の形式で表示する。

---

## SPEC-44: ノードファイルはプレーンテキスト .md（normal・アンブレラ）

<details><summary>⬡ SPEC-44 · v0.2</summary>

```yaml
id: SPEC-44
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-1
    ref_version: "0.4"
  - to: FND-67
    ref_version: "0.1"
```
</details>

**概要**: in-graph ファイルの UTF-8 プレーンテキスト検証を、正常読込（SPEC-44-1）・BOM 検出 WARNING（SPEC-44-2）・デコードエラー ERROR（SPEC-44-3）の入力クラス別に子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-44-1: 正常 UTF-8 ファイルの読み込みが完了（normal）

<details><summary>⬡ SPEC-44-1 · v0.1</summary>

```yaml
id: SPEC-44-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-44
    ref_version: "0.2"
```
</details>

**前提条件**: `trace_scope.include` に一致する in-graph ファイルが1件以上存在し、いずれも BOM なしの正常な UTF-8 でエンコードされている。
**入力/トリガ**: 検証ツールが in-graph ファイルを `file.read_text(encoding='utf-8', errors='strict')` で読み込む。
**期待動作**: 正常 UTF-8 ファイルを読み込んだとき、全 in-graph ファイルの読み込みがエラーなく完了する（違反 0 件）。
**例**: `doc-system/02-what/01-fr.md` を `open(..., encoding='utf-8', errors='strict').read()` → 読み込み成功 → 違反 0 件。

---

## SPEC-44-2: BOM 付きファイルに WARNING を1件出力（boundary）

<details><summary>⬡ SPEC-44-2 · v0.1</summary>

```yaml
id: SPEC-44-2
type: SPEC
labels: []
scheduled: ""
condition: boundary
edges:
  - to: SPEC-44
    ref_version: "0.2"
```
</details>

**前提条件**: `trace_scope.include` に一致する in-graph ファイルのうち1件が、先頭に BOM（`\xEF\xBB\xBF`）を持つ。
**入力/トリガ**: 検証ツールが当該ファイルを読み込み、先頭 BOM を検出する。
**期待動作**: 先頭 BOM を検出したとき、当該ファイルに対し WARNING を1件出力する。
**例**: `doc-system/02-what/01-fr.md` の先頭に BOM が存在 → 当該ファイルに WARNING を1件出力する。

---

## SPEC-44-3: UTF-8 デコードエラー発生ファイルに ERROR を1件出力（error）

<details><summary>⬡ SPEC-44-3 · v0.1</summary>

```yaml
id: SPEC-44-3
type: SPEC
labels: []
scheduled: ""
condition: error
edges:
  - to: SPEC-44
    ref_version: "0.2"
```
</details>

**前提条件**: `trace_scope.include` に一致する in-graph ファイルのうち1件が、UTF-8 として不正なバイト列を含む。
**入力/トリガ**: 検証ツールが当該ファイルを `errors='strict'` で読み込み、UTF-8 デコードエラーに遭遇する。
**期待動作**: UTF-8 デコードエラーが発生したとき、当該ファイルに対し ERROR を1件出力する。
**例**: バイナリデータを含む `doc-system/corrupt.md` が in-graph に存在 → `ERROR|doc-system/corrupt.md:0|NFR-1-check|(none)|UTF-8 decode error` を出力する。

---

## SPEC-45: spec-inspector は Python 標準ライブラリのみ使用（normal・アンブレラ）

<details><summary>⬡ SPEC-45 · v0.2</summary>

```yaml
id: SPEC-45
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-2
    ref_version: "0.3"
  - to: FND-68
    ref_version: "0.1"
  - to: FND-90
    ref_version: "0.1"
```
</details>

**概要**: spec-inspector の標準ライブラリ限定要件を、標準ライブラリ参照判定（SPEC-45-1）と外部 import 検出時の ERROR 出力（SPEC-45-2）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-45-1: 全 import が標準ライブラリのみを参照する（normal）

<details><summary>⬡ SPEC-45-1 · v0.2</summary>

```yaml
id: SPEC-45-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-45
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector の実装ソースファイル群が1件以上存在し、静的解析が完了している。
**入力/トリガ**: CI が全ソースファイルの `import X` 文および `from X import Y` 文を抽出する。
**期待動作**: 全ソースファイルの import 文を解析したとき、外部パッケージ（PyYAML・requests・pydantic 等）への依存が 0 件であることを判定する。
**例**: `src/inspector.py` の全 import が `import sys`, `import os`, `import re`, `import pathlib`, `import json` のみ → 外部依存 0 件 → 違反なし。

---

## SPEC-45-2: 外部パッケージ import 検出時に ERROR を出力する（failure）

<details><summary>⬡ SPEC-45-2 · v0.2</summary>

```yaml
id: SPEC-45-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-45
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector の実装ソースファイル群が1件以上存在し、静的解析が完了している。
**入力/トリガ**: CI が外部パッケージへの `import` 文を1件以上検出する。
**期待動作**: 外部パッケージ import を検出したとき、当該行を指す ERROR を1件出力する。
**例**: `import yaml` が `src/parser.py` 行3に存在 → `ERROR|src/parser.py:3|NFR-2-check|(none)|external package import: yaml` を出力。

---

## SPEC-46: スキルファイルは外部ファイル参照なしに自己完結（normal・アンブレラ）

<details><summary>⬡ SPEC-46 · v0.2</summary>

```yaml
id: SPEC-46
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-3
    ref_version: "0.2"
  - to: FND-69
    ref_version: "0.1"
  - to: FND-90
    ref_version: "0.1"
```
</details>

**概要**: スキルファイルの外部参照自己完結要件を、外部参照パターン非存在の判定（SPEC-46-1）と検出時の WARNING 出力（SPEC-46-2）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-46-1: スキルファイルに外部参照パターンが存在しない（normal）

<details><summary>⬡ SPEC-46-1 · v0.2</summary>

```yaml
id: SPEC-46-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-46
    ref_version: "0.2"
```
</details>

**前提条件**: スキルファイルが1件以上存在し、全行が外部参照パターンで検索済みである。
**入力/トリガ**: asset-auditor がスキルファイルの全行を外部参照パターン（`\.\./`・`^include:`・`^source:`・`@import`）で検索する。
**期待動作**: スキルファイルを全行検索したとき、外部ファイル参照パターンにマッチする行が 0 件であることを判定する。
**例**: `.claude/skills/spec-author/SKILL.md` を全行検索 → `../`・`include:`・`source:`・`@import` にマッチする行なし → 違反なし。

---

## SPEC-46-2: 外部参照パターン検出時に WARNING を出力する（failure）

<details><summary>⬡ SPEC-46-2 · v0.2</summary>

```yaml
id: SPEC-46-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-46
    ref_version: "0.2"
```
</details>

**前提条件**: スキルファイルが1件以上存在し、全行が外部参照パターンで検索済みである。
**入力/トリガ**: asset-auditor が外部参照パターンにマッチする行を1件以上検出する。
**期待動作**: 外部参照パターンにマッチする行を検出したとき、当該行を指す WARNING を1件出力する。
**例**: `.claude/skills/spec-author/SKILL.md` 行42に `see: ../07-authoring-guide.md` が存在 → `WARNING|.claude/skills/spec-author/SKILL.md:42|NFR-3-check|(none)|external file reference: ../07-authoring-guide.md` を出力。

---

## SPEC-47: 全 in-graph ノードの summary バッジに version（x.y）が存在する（normal・アンブレラ）

<details><summary>⬡ SPEC-47 · v0.2</summary>

```yaml
id: SPEC-47
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-4
    ref_version: "0.2"
  - to: FND-84
    ref_version: "0.1"
  - to: FND-70
    ref_version: "0.1"
```
</details>

**概要**: ノードバッジ version の存在・形式要件を、形式適合判定（SPEC-47-1）と欠如・形式不正時の ERROR 出力（SPEC-47-2）に分けて子 SPEC で検証する（傘ノード・非テスタブル。DD-8：ファイルレベルフロントマター廃止・ノードバッジが唯一の版管理真実源）。

---

## SPEC-47-1: 全ノードのバッジが `· vX.Y`（非負整数 2 部）形式を持つ（normal）

<details><summary>⬡ SPEC-47-1 · v0.1</summary>

```yaml
id: SPEC-47-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-47
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph にノードが1件以上存在し、各ノードの summary バッジが走査済みである。
**入力/トリガ**: 検証ツールが全ノードの summary バッジから `· vX.Y` 部分を抽出する。
**期待動作**: 全 in-graph ノードのバッジを走査したとき、各バッジが `· vX.Y`（X・Y はそれぞれ非負整数）の 2 部形式を持つことを判定する。
**合格例**: `⬡ FR-1 · v0.3` → バッジ version = "0.3"（X=0, Y=3）・形式適合 → 違反なし。`⬡ SPEC-54 · v0.1` → 違反なし。

---

## SPEC-47-2: バッジ version 欠如・形式不正のノードに ERROR を出力する（failure）

<details><summary>⬡ SPEC-47-2 · v0.1</summary>

```yaml
id: SPEC-47-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-47
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph にノードが1件以上存在し、各ノードの summary バッジが走査済みである。
**入力/トリガ**: 検証ツールが `· v` 部分の欠如、または `X.Y` が非負整数 2 部形式でないバッジを1件以上検出する。
**期待動作**: バッジ version 欠如または形式不正を検出したとき、当該ノードを指す ERROR を1件出力する。
**違反例**: `⬡ SPEC-99`（`· vX.Y` 部分なし）→ `ERROR|{file}:{line}|NFR-4-check|SPEC-99|node badge version missing` を出力。`⬡ SPEC-88 · v2`（Y 部分欠如）→ `ERROR|{file}:{line}|NFR-4-check|SPEC-88|node badge version format error: v2` を出力。

---

## SPEC-48: 各ノードは直接の親のみへ辺を張る（USDM 1段制約）（normal・アンブレラ）

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
  - to: FND-25
    ref_version: "0.1"
  - to: FND-71
    ref_version: "0.1"
```
</details>

**概要**: USDM 1 段制約（直接親のみへの辺）の検証を、全辺が直接親型を指す判定（SPEC-48-1）と祖先辺検出時の ERROR 出力（SPEC-48-2）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-48-1: SPEC の辺が全て直接親型（FR/NFR/SPEC）を指す（normal）

<details><summary>⬡ SPEC-48-1 · v0.1</summary>

```yaml
id: SPEC-48-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-48
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph に SPEC ノードが1件以上存在し、全ノードがパース済みである。
**入力/トリガ**: 検証ツールが SPEC ノードの `edges[].to` を走査する。
**期待動作**: SPEC ノードの全辺を走査したとき、各辺が FR・NFR・または別 SPEC（直接親）を指し、祖先型（SR・VAL 等）への直接辺が 0 件であることを判定する。
**例**: `SPEC-1` の edges が `[{to: "FR-1", ref_version: "0.2"}]` → 直接親 FR-1 のみ参照 → 違反なし。

---

## SPEC-48-2: 祖先型への直接辺検出時に ERROR を出力する（failure）

<details><summary>⬡ SPEC-48-2 · v0.1</summary>

```yaml
id: SPEC-48-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-48
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph に SPEC ノードが1件以上存在し、全ノードがパース済みである。
**入力/トリガ**: 検証ツールが SPEC ノードの `edges[].to` に祖先型（SR・VAL 等）への直接辺を1件以上検出する。
**期待動作**: 祖先型への直接辺を検出したとき、当該辺を指す ERROR を1件出力する。
**例**: `SPEC-99` の edges に `{to: "SR-2", ref_version: "0.2"}` が含まれる → `ERROR|{file}:{line}|NFR-5-check|SPEC-99|direct ancestor edge to SR-2 violates 1-level constraint` を出力。

---

## SPEC-49: DD/Q/PEND のノード YAML（メタ属性）に status 系フィールドが存在しない（normal・アンブレラ）

<details><summary>⬡ SPEC-49 · v0.2</summary>

```yaml
id: SPEC-49
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: NFR-6
    ref_version: "0.3"
  - to: FND-72
    ref_version: "0.1"
  - to: FND-85
    ref_version: "0.1"
```
</details>

**概要**: DD・Q・PEND ノードのライフサイクル状態がノード YAML（メタ属性）に漏れていないことの検証を、キー非存在の正常判定（SPEC-49-1）とキー存在時の WARNING 出力（SPEC-49-2）に分けて子 SPEC で検証する（傘ノード・非テスタブル。状態は本文見出しバッジにのみ記載し、ノード YAML には持たない＝DD-8 でファイル frontmatter は廃止済み）。

---

## SPEC-49-1: status 系キー非存在ノードは違反なし（normal）

<details><summary>⬡ SPEC-49-1 · v0.2</summary>

```yaml
id: SPEC-49-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-49
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に `type: DD`・`type: Q`・`type: PEND` のいずれかのノードが1件以上存在し、ライフサイクル状態は本文見出しバッジ（`**status: open**` 等）にのみ記載されている。
**入力/トリガ**: 検証ツールが、ノード YAML（メタ属性）に `status:`・`lifecycle:`・`state:` キーを持たない DD・Q・PEND ノードを検査する。
**期待動作**: status 系キーがノード YAML（メタ属性）に存在しないとき、当該ノードを違反なしとして通過させる。
**例**: `{id: "DD-5", type: "DD", labels: [], scheduled: "", edges: []}` → status 系フィールドなし → 違反なし。

---

## SPEC-49-2: status 系キー存在で WARNING 出力（failure）

<details><summary>⬡ SPEC-49-2 · v0.2</summary>

```yaml
id: SPEC-49-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-49
    ref_version: "0.2"
```
</details>

**前提条件**: in-graph に `type: DD`・`type: Q`・`type: PEND` のいずれかのノードが1件以上存在し、ライフサイクル状態は本文見出しバッジに記載されるべきものである。
**入力/トリガ**: 検証ツールが、ノード YAML（メタ属性）に `status:`・`lifecycle:`・`state:` のいずれかのキーを持つ DD・Q・PEND ノードを検査する。
**期待動作**: status 系キーがノード YAML（メタ属性）に存在するとき、WARNING を1件出力する。
**例**: `{id: "Q-3", type: "Q", labels: [], scheduled: "", status: "open", edges: []}` → `WARNING|{file}:{line}|NFR-6-check|Q-3|lifecycle field 'status' in node YAML violates NFR-6` を出力。

---

## SPEC-50: --export-graph による依存グラフファイル出力（normal・アンブレラ）

<details><summary>⬡ SPEC-50 · v0.2</summary>

```yaml
id: SPEC-50
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: FR-15
    ref_version: "0.1"
  - to: FND-78
    ref_version: "0.1"
  - to: FND-73
    ref_version: "0.1"
```
</details>

**概要**: `--export-graph` 実行時の依存グラフ出力を、ファイル生成（SPEC-50-1）・stdout 無エラー（SPEC-50-2）・exit code 0（SPEC-50-3）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-50-1: --export-graph で指定フォーマットのグラフファイルを生成（normal・post-mvp）

<details><summary>⬡ SPEC-50-1 · v0.1</summary>

```yaml
id: SPEC-50-1
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-50
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector がノードグラフを正常にパース済みで（SPEC-1 の正常系が先行）、グラフに1件以上のノードが存在し、`--export-graph` に有効なフォーマット名（`dot` または `json`）と出力先ファイルパスが指定されている。
**入力/トリガ**: `spec-inspector --export-graph dot ./output/graph.dot`（または `json` フォーマット・任意の出力先パス）を実行する。
**期待動作**: `--export-graph` を実行したとき、指定フォーマット（`dot`＝Graphviz dot 形式・`json`＝JSON 隣接リスト形式）で依存関係グラフを指定ファイルパスに書き出す。
**合格例**: ノード 3 件（SPEC-1→FR-1、FR-1→SR-1）に `--export-graph dot ./graph.dot` を実行 → `./graph.dot` に `digraph { "SPEC-1" -> "FR-1"; "FR-1" -> "SR-1"; }` 形式の dot ファイルが生成される。
**違反例**: 出力ファイルが生成されない・または dot 形式として不正なテキスト（例: JSON 形式）が書き出される → 期待動作を満たさない。

---

## SPEC-50-2: --export-graph 正常時 stdout にエラーを出力しない（normal・post-mvp）

<details><summary>⬡ SPEC-50-2 · v0.1</summary>

```yaml
id: SPEC-50-2
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-50
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector がノードグラフを正常にパース済みで、グラフに1件以上のノードが存在し、`--export-graph` に有効なフォーマット名と出力先ファイルパスが指定され、グラフファイルが正常に書き出される。
**入力/トリガ**: `spec-inspector --export-graph dot ./output/graph.dot` を実行する。
**期待動作**: グラフファイル出力が正常完了したとき、stdout にエラーメッセージを出力しない。
**合格例**: `--export-graph dot ./graph.dot` 実行でファイルが正常生成され、stdout にエラーメッセージが現れない。
**違反例**: ファイルは生成されたが stdout にエラーメッセージが出力される → 期待動作を満たさない。

---

## SPEC-50-3: --export-graph 正常時 exit code 0 で終了（normal・post-mvp）

<details><summary>⬡ SPEC-50-3 · v0.1</summary>

```yaml
id: SPEC-50-3
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-50
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector がノードグラフを正常にパース済みで、グラフに1件以上のノードが存在し、`--export-graph` に有効なフォーマット名と出力先ファイルパスが指定され、グラフファイルが正常に書き出される。
**入力/トリガ**: `spec-inspector --export-graph dot ./output/graph.dot` を実行する。
**期待動作**: グラフファイル出力が正常完了したとき、exit code 0 で終了する。
**合格例**: `--export-graph dot ./graph.dot` 実行でファイルが正常生成され、プロセスが exit code 0 で終了する。
**違反例**: ファイルは生成されたが exit code が 0 以外で終了する → 期待動作を満たさない。

---

## SPEC-51: --complexity による参照関係複雑度メトリクスレポート stdout 出力（normal・アンブレラ）

<details><summary>⬡ SPEC-51 · v0.2</summary>

```yaml
id: SPEC-51
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: FR-16
    ref_version: "0.1"
  - to: FND-78
    ref_version: "0.1"
  - to: FND-74
    ref_version: "0.1"
```
</details>

**概要**: `--complexity` 実行時のメトリクスレポート出力を、レポート stdout 出力（SPEC-51-1）と exit code 0（SPEC-51-2）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-51-1: --complexity でメトリクスレポートを stdout 出力（normal・post-mvp）

<details><summary>⬡ SPEC-51-1 · v0.1</summary>

```yaml
id: SPEC-51-1
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-51
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector がノードグラフを正常にパース済みで（SPEC-1 の正常系が先行）、グラフに1件以上のノードが存在し、`--complexity` オプションが指定されている。
**入力/トリガ**: `spec-inspector --complexity` を実行する。
**期待動作**: `--complexity` 指定時、各ノードの in-degree・out-degree・ハブ判定を含むメトリクスレポートを id 昇順の行形式（`{node-id} | in={N} | out={N} | hub={yes/no}`）で stdout に出力する。
**合格例**: ノード FR-1（被参照: SPEC-1, SPEC-2 の 2 件、参照先: SR-1 の 1 件）を含むグラフに `--complexity` 実行 → stdout に `FR-1 | in=2 | out=1 | hub=no` が含まれる。
**違反例**: stdout に何も出力されない・またはメトリクス行に `in=` / `out=` フィールドが欠落する → 期待動作を満たさない。

---

## SPEC-51-2: --complexity 正常時 exit code 0 で終了（normal・post-mvp）

<details><summary>⬡ SPEC-51-2 · v0.1</summary>

```yaml
id: SPEC-51-2
type: SPEC
labels: [post-mvp]
scheduled: "sprint-2"
condition: normal
edges:
  - to: SPEC-51
    ref_version: "0.2"
```
</details>

**前提条件**: spec-inspector がノードグラフを正常にパース済みで、グラフに1件以上のノードが存在し、`--complexity` オプションが指定され、メトリクスレポートが正常に出力される。
**入力/トリガ**: `spec-inspector --complexity` を実行する。
**期待動作**: メトリクスレポート出力が正常完了したとき、exit code 0 で終了する。
**合格例**: `--complexity` 実行でレポートが stdout に出力され、プロセスが exit code 0 で終了する。
**違反例**: レポートは出力されたが exit code が 0 以外で終了する → 期待動作を満たさない。

---

## SPEC-52: I-1 完全フィールドスキーマ適合（normal・アンブレラ）

<details><summary>⬡ SPEC-52 · v0.1</summary>

```yaml
id: SPEC-52
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-1
    ref_version: "0.3"
  - to: FND-18
    ref_version: "0.1"
  - to: FND-75
    ref_version: "0.1"
```
</details>

**概要**: 完全フィールドスキーマ適合ノードがスキーマ検証を通過することの検証を、RULE-025（SPEC-52-1）・RULE-026（SPEC-52-2）・RULE-027（SPEC-52-3）・RULE-028（SPEC-52-4）の各非発火と終了コード 0（SPEC-52-5）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-52-1: 完全スキーマ適合ノードは RULE-025 を発火させない（normal）

<details><summary>⬡ SPEC-52-1 · v0.1</summary>

```yaml
id: SPEC-52-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-52
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みであり、当該ノードは共通必須フィールドと型別必須拡張フィールドを全て備える。
**入力/トリガ**: 検証ツールが、共通必須フィールド（`id`・`type`・`labels`・`scheduled`・`edges`）と型別必須拡張フィールド（SPEC/TD は `condition`、TR は `result` と `log_ref`）を全て備えたノードに RULE-025 を評価する。
**期待動作**: 完全スキーマ適合ノードに対して RULE-025 を発火させない。
**例**: `{id: "FR-1", type: "FR", labels: [], scheduled: "", edges: [{to: "SR-2", ref_version: "0.2"}]}` を処理 → RULE-025 非発火。

---

## SPEC-52-2: 完全スキーマ適合ノードは RULE-026 を発火させない（normal）

<details><summary>⬡ SPEC-52-2 · v0.1</summary>

```yaml
id: SPEC-52-2
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-52
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みであり、当該ノードは共通必須フィールドと型別必須拡張フィールドを全て備える。
**入力/トリガ**: 検証ツールが、共通必須フィールドと型別必須拡張フィールドを全て備えたノードに RULE-026 を評価する。
**期待動作**: 完全スキーマ適合ノードに対して RULE-026 を発火させない。
**例**: `{id: "FR-1", type: "FR", labels: [], scheduled: "", edges: [{to: "SR-2", ref_version: "0.2"}]}` を処理 → RULE-026 非発火。

---

## SPEC-52-3: 完全スキーマ適合ノードは RULE-027 を発火させない（normal）

<details><summary>⬡ SPEC-52-3 · v0.1</summary>

```yaml
id: SPEC-52-3
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-52
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みであり、当該ノードは共通必須フィールドと型別必須拡張フィールドを全て備える。
**入力/トリガ**: 検証ツールが、共通必須フィールドと型別必須拡張フィールドを全て備えたノードに RULE-027 を評価する。
**期待動作**: 完全スキーマ適合ノードに対して RULE-027 を発火させない。
**例**: `{id: "FR-1", type: "FR", labels: [], scheduled: "", edges: [{to: "SR-2", ref_version: "0.2"}]}` を処理 → RULE-027 非発火。

---

## SPEC-52-4: 完全スキーマ適合ノードは RULE-028 を発火させない（normal）

<details><summary>⬡ SPEC-52-4 · v0.1</summary>

```yaml
id: SPEC-52-4
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-52
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みであり、当該ノードは共通必須フィールドと型別必須拡張フィールドを全て備える。
**入力/トリガ**: 検証ツールが、共通必須フィールドと型別必須拡張フィールドを全て備えたノードに RULE-028 を評価する。
**期待動作**: 完全スキーマ適合ノードに対して RULE-028 を発火させない。
**例**: `{id: "FR-1", type: "FR", labels: [], scheduled: "", edges: [{to: "SR-2", ref_version: "0.2"}]}` を処理 → RULE-028 非発火。

---

## SPEC-52-5: スキーマ違反 0 件のとき終了コード 0（normal）

<details><summary>⬡ SPEC-52-5 · v0.1</summary>

```yaml
id: SPEC-52-5
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-52
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph の全ノードがフィールドスキーマ検証（RULE-025/026/027/028）を通過し、スキーマ違反が 0 件である。
**入力/トリガ**: 検証ツールがフィールドスキーマ検証を全ノードに対して完了する。
**期待動作**: フィールドスキーマ違反が 0 件のとき、プロセス終了コードを 0 とする。
**例**: 全ノードが完全スキーマ適合で違反 0 件 → 終了コード 0。

---

## SPEC-53: 共通必須フィールドの型不正・欠如検出（failure・RULE-028・アンブレラ）

<details><summary>⬡ SPEC-53 · v0.1</summary>

```yaml
id: SPEC-53
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: FR-1
    ref_version: "0.3"
  - to: FND-18
    ref_version: "0.1"
  - to: FND-76
    ref_version: "0.1"
```
</details>

**概要**: 共通必須フィールド（`labels`・`scheduled`・`edges`）の型不正・欠如検出（RULE-028）を、ERROR 出力（SPEC-53-1）・後続 RULE 中断（SPEC-53-2）・終了コード（SPEC-53-3）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-53-1: 共通必須フィールド違反の ERROR 出力（failure・RULE-028）

<details><summary>⬡ SPEC-53-1 · v0.1</summary>

```yaml
id: SPEC-53-1
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-53
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡ PREFIX-N` マーカー直後の YAML ブロックから 1 件のノードが生成済みである。`id`・`type` の欠如/空は RULE-025/026 が、edge の `ref_version` 欠如は RULE-027 が担当するため適合済みとし、本検査は共通必須フィールド `labels`・`scheduled`・`edges` の存在と型のみを評価する。
**入力/トリガ**: 検証ツールが、`labels` が非リスト・`scheduled` が非文字列・`edges` が非リスト・またはこれら 3 キーのいずれかが欠如、のいずれか 1 つに該当するノードを処理する。
**期待動作**: 当該違反があるとき、RULE-028 ERROR を 1 件出力する。
**出力フォーマット**: `ERROR|{file}:{line}|RULE-028|{id}|{message}`（`|` 区切り 5 フィールド。`{file}` は in-graph 相対パス、`{line}` は当該ノードの `⬡` マーカー行番号、`{message}` は違反フィールド名と期待型を述べる文）。
**例**: ノード `{id: "SPEC-99", type: "SPEC", labels: "foo", scheduled: "", edges: []}`（`labels` が文字列）を `doc-system/02-what/03-spec.md` の当該マーカー行で処理 → `ERROR|doc-system/02-what/03-spec.md:{line}|RULE-028|SPEC-99|field 'labels' must be a list` を 1 件出力。

---

## SPEC-53-2: 共通必須フィールド違反ノードの後続 RULE 中断（failure・RULE-028）

<details><summary>⬡ SPEC-53-2 · v0.1</summary>

```yaml
id: SPEC-53-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-53
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph ファイルが PyYAML safe_load でパース可能で、`⬡` マーカー直後の YAML から 1 件のノードが生成済み。`labels`・`scheduled`・`edges` の型/存在検査（SPEC-53-1）が当該ノードで違反を検出している。
**入力/トリガ**: 検証ツールが、共通必須フィールド違反（RULE-028）を検出したノードについて以降の処理を進める。
**期待動作**: 当該ノードに対して共通必須フィールド違反が検出されたとき、そのノードに対する後続 RULE 評価を中断する（他ファイル・他ノードの処理は継続）。
**例**: `labels` が文字列の SPEC-99 を処理 → RULE-028 違反検出後、SPEC-99 に対する後続 RULE 評価を実行せず、次ノードの処理へ進む。

---

## SPEC-53-3: 共通必須フィールド違反時のプロセス終了コード（failure・RULE-028）

<details><summary>⬡ SPEC-53-3 · v0.1</summary>

```yaml
id: SPEC-53-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-53
    ref_version: "0.1"
```
</details>

**前提条件**: in-graph 全ファイルの検証処理が完了し、RULE-028（共通必須フィールド）違反件数が集計済みである。
**入力/トリガ**: 検証ツールが、RULE-028 違反を 1 件以上検出した状態でプロセスを終了する。
**期待動作**: RULE-028 違反が 1 件以上あるとき、プロセス終了コードを 1 とする。
**例**: `labels` が文字列の SPEC-99 を含む in-graph を検証 → RULE-028 違反 1 件以上のため、プロセス終了コード 1 で終了。

---

## SPEC-54: 著作は記載内容入力を必須とする（normal・アンブレラ）

<details><summary>⬡ SPEC-54 · v0.1</summary>

```yaml
id: SPEC-54
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-13
    ref_version: "0.1"
  - to: FND-77
    ref_version: "0.1"
```
</details>

**概要**: 著作（P-7-1）が記載内容（I-9）を必須とすることの検証を、I-7+I-9 充填による草案生成（SPEC-54-1）・I-9 欠如時の O-3 生成不可（SPEC-54-2）・I-7 単独時の O-3 生成不可（SPEC-54-3）に分けて子 SPEC で検証する（傘ノード・非テスタブル）。

---

## SPEC-54-1: 著作は I-7 と I-9 を充填して草案を生成する（normal）

<details><summary>⬡ SPEC-54-1 · v0.1</summary>

```yaml
id: SPEC-54-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: SPEC-54
    ref_version: "0.1"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在し、著者（ACTOR-1）が著作要求（E-2）を起こす。
**入力/トリガ**: 著者が P-7-1（著作）に、テンプレート（I-7）と著作対象ノードの記載内容（I-9：型・親 ID・依存辺・本文項目の指定）の両方を入力として与える。
**期待動作**: I-7 と I-9 の両方が与えられたとき、P-7-1 は記載内容を I-7 のテンプレート構造に充填してノード草案（tmp）を生成する。
**例**: 著者が「type: FR・親 SR-1・本文4項目」という I-9 を I-7（FR テンプレート）とともに P-7-1 に渡す → tmp 草案が生成される。

---

## SPEC-54-2: I-9 欠如時は O-3 を生成しない（failure）

<details><summary>⬡ SPEC-54-2 · v0.1</summary>

```yaml
id: SPEC-54-2
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-54
    ref_version: "0.1"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在し、著者（ACTOR-1）が著作要求（E-2）を起こす。
**入力/トリガ**: 著者が P-7-1（著作）に、記載内容（I-9）を与えずに著作を要求する。
**期待動作**: I-9（記載内容）が与えられないとき、著作対象が定まらず P-7-1 は O-3（著作済みノードファイル）を生成しない（著作不成立）。
**例**: 著者が I-9 を与えず P-7-1 に著作を要求する → 著作対象不定のため O-3 は生成されない。

---

## SPEC-54-3: I-7 のみでは O-3 を生成しない（failure）

<details><summary>⬡ SPEC-54-3 · v0.1</summary>

```yaml
id: SPEC-54-3
type: SPEC
labels: []
scheduled: ""
condition: failure
edges:
  - to: SPEC-54
    ref_version: "0.1"
```
</details>

**前提条件**: `.claude/agents/` に型別著作エージェント定義が存在し、著者（ACTOR-1）が著作要求（E-2）を起こす。
**入力/トリガ**: 著者が P-7-1（著作）に、テンプレート（I-7）のみを与え、記載内容（I-9）を伴わずに著作を要求する。
**期待動作**: 入力が I-7（構造の雛形）のみであるとき、P-7-1 は O-3（著作済みノードファイル）を生成しない。
**例**: 著者が I-9 を与えず I-7（テンプレート）のみを P-7-1 に渡す → O-3 は生成されない。
