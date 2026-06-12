---
version: "0.1.1"
---
# 指摘・Finding — doc-system ドッグフーディング（要件〜分析層）

> **型**: FND ／ **必須**: 指摘対象要素への依存辺が1本以上（RULE-006 config: `must_link_to: FND → any`）
> 無名依存辺のみ（`kind`/`status` なし・`to` は単数・全辺に `ref_version` 必須）。
> 要件フェーズのため、指摘対象ノード自体は未修正（オーナー判断待ちの記録）。

---

## FND-1: ACTOR-3（spec-inspector）の系境界誤り（被依存辺ゼロ）

<details><summary>⬡ FND-1 · v0.1</summary>

```yaml
id: FND-1
type: FND
labels: []
scheduled: ""
edges:
  - to: ACTOR-3
    ref_version: "0.2"
```
</details>

**深刻度**: ERROR
**内容**: ACTOR-3（spec-inspector）は外部 ACTOR として置かれているが、spec-inspector は本システム（検証 CLI）そのもの＝**系内処理**であり、既存の P-1〜P-4 と同一実体の二重表現である。out 辺は `→SR-4` のみで、E/I/O いずれからも被依存辺を受けず（`must_be_linked_from: ACTOR ← [E,I,O]` 違反・実質孤立に近い）、価値到達経路から浮いている。系外＝非アクタ（PR3/PR4）の原則に反する。
**対応状況**: resolved
**対応内容**: ACTOR-3 を削除し、spec-inspector を系内処理（P-1〜P-4）へ一本化した（actors.md v0.2→0.3）。ACTOR-3 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。

---

## FND-2: P-2「RULE 検査」の単一責務違反（粒度過大）

<details><summary>⬡ FND-2 · v0.1</summary>

```yaml
id: FND-2
type: FND
labels: []
scheduled: ""
edges:
  - to: P-2
    ref_version: "0.5"
```
</details>

**深刻度**: WARNING
**内容**: P-2 が構造完結性（RULE-005〜008）・ドリフト（RULE-001/002/004/022）・カバレッジ（RULE-016〜019）・検証層（RULE-006/020/021）の全 RULE 群を1プロセスに内包している。対応 SPEC が SPEC-5〜23 と多数に分かれているのに、P-2 だけがそれらを束ねており、DFD レベリング上の単一責務の疑いがある。
**対応状況**: resolved
**対応内容**: DFD レベリングにより P-2 を P-2-1（ドリフト・義務辺）・P-2-2（構造完結性）・P-2-3（カバレッジ属性）・P-2-4（検証層完結性）の4子プロセスへ分解した（processes.md v0.4→0.5）。P-2 に `→FND-2` バックリファレンス辺を付与済み。

---

## FND-3: events.md の E-2 欠番

<details><summary>⬡ FND-3 · v0.1</summary>

```yaml
id: FND-3
type: FND
labels: []
scheduled: ""
edges:
  - to: E-1
    ref_version: "0.4"
```
</details>

**深刻度**: WARNING
**内容**: events.md は E-1・E-3 のみで E-2 が欠番。E-1 のスティミュラス「仕様著者または CI」は CI 駆動を含意しており、CI 定期/フック起動が別事象として落ちている疑いがある。削除なら理由、別事象なら起票が必要。
**対応状況**: resolved
**対応内容**: E-3（著作要求）を E-2 へリネームして欠番を補正した（events.md・processes.md P-7 参照追従）。E-2 に `→FND-3` バックリファレンス辺を付与済み。

---

## FND-4: カバレッジ点検（グラフ網羅性）の上流 SPEC 欠落

<details><summary>⬡ FND-4 · v0.1</summary>

```yaml
id: FND-4
type: FND
labels: []
scheduled: ""
edges:
  - to: P-3
    ref_version: "0.5"
```
</details>

**深刻度**: WARNING
**内容**: P-3「カバレッジ点検」本文は「孤児ノード・未駆動出力・未定義反応」（グラフ網羅性点検）と「SPEC×condition×TD」の2系統を担うが、P-3 の依存先は SPEC-14 のみである。前者のグラフ網羅性点検に対応する SPEC が spec.md に存在せず、FR/SPEC の裏付けがない機能が分析層に出現している＝価値経路の上流欠落（PR6）。
**対応状況**: resolved
**対応内容**: SPEC-29（正常系）・SPEC-30（接続漏れ検出）を FR-3 配下に新設し、P-3 を P-3-1（グラフ網羅性）・P-3-2（仕様カバレッジ計測）に分解した（spec.md・processes.md v0.5）。P-3・SPEC-29・SPEC-30 に `→FND-4` バックリファレンス辺を付与済み。

---

## FND-5: FR-6 本文が廃止 RULE-015 を生きた番号として参照

<details><summary>⬡ FND-5 · v0.1</summary>

```yaml
id: FND-5
type: FND
labels: []
scheduled: ""
edges:
  - to: FR-6
    ref_version: "0.2"
```
</details>

**深刻度**: WARNING
**内容**: FR-6 本文は「TD の verifies 欠如（RULE-015）」を現役ルールとして記載するが、正本では RULE-015 は廃止され `must_be_linked_from: SPEC←[TD]`（RULE-006）に吸収済みである（docs/doc-system/05-verification.md L74・spec.md SPEC-15-1 は正しく「旧 RULE-015」と記述）。FR-6 のみ記述が旧モデルに取り残されている。
**対応状況**: resolved
**対応内容**: FR-6 本文の「TD の verifies 欠如（RULE-015）」を「SPEC への TD 被依存辺欠如（`must_be_linked_from: SPEC←[TD]`・RULE-006・旧 RULE-015）」へ修正した（fr.md）。FR-6 に `→FND-5` バックリファレンス辺を付与済み。

---

## FND-6: I-2/I-3/I-4 の過分割の疑い

<details><summary>⬡ FND-6 · v0.1</summary>

```yaml
id: FND-6
type: FND
labels: []
scheduled: ""
edges:
  - to: I-2
    ref_version: "0.5"
```
</details>

**深刻度**: INFO
**内容**: suppress(I-2)/scheduled(I-3)/ref_version(I-4) を I-1（ノードファイル）と独立の入力に割っているが、いずれも著者がノードファイル内に書く値で、発生源・もの（ファイル）が同一である。PR1（もの＋発生源で分ける／使い道だけで割らない）に照らすと過分割の疑いがある。ただし各々が別 SPEC（SPEC-22/20/9）に紐づき追跡価値はある。
**対応状況**: open
**対応内容**: （推奨）要件段では現状維持（追跡価値が分割コストを上回る）。設計段で DM/CFG に落とすときに再評価。info 据え置き。

---

## FND-7: E-2 スティミュラスが「新規ノード著作」のみで既存ノード改訂を含まない

<details><summary>⬡ FND-7 · v0.1</summary>

```yaml
id: FND-7
type: FND
labels: []
scheduled: ""
edges:
  - to: E-2
    ref_version: "0.5"
```
</details>

**深刻度**: WARNING
**内容**: E-2（著作要求）のスティミュラスが「仕様著者（ACTOR-1）が**新規ノード著作**を決定し」と記述されており、既存ノードの内容変更・辺追加・バージョンバンプといった改訂操作が同じ著作フロー（P-7 → reconciliation）を通るにもかかわらずイベント定義から漏れていた。E は系外アクタが入力を持ち込んで起こす事象であり、新規作成と既存改訂は同一事象のバリアントとして定義すべきだった。
**対応状況**: resolved
**対応内容**: E-2 スティミュラスを「ノード著作（新規作成または既存改訂）を決定し」へ修正した（events.md v0.4→0.5）。E-2 に `→FND-7` バックリファレンス辺を付与済み。

---

## FND-8: D-2「著作済みノードファイル」の型分類誤り（D→O）

<details><summary>⬡ FND-8 · v0.1</summary>

```yaml
id: FND-8
type: FND
labels: []
scheduled: ""
edges:
  - to: O-3
    ref_version: "0.6"
```
</details>

**深刻度**: ERROR
**内容**: 旧 D-2「著作済みノードファイル」が D（内部データフロー・系外へ出ない）として分類されていた。しかしイベントの定義は「系外アクタが入力を持ち込み、プロセスがアクションを行い、外部アクタへのレスポンスが生成される」であり、E-2（著作要求）のレスポンスは O 型（系外アクタ宛の出力）でなければならない。D 型では O→ACTOR 辺が持てず ACTOR-1 への価値到達が表現できなかった。
**対応状況**: resolved
**対応内容**: D-2 を削除し O-3（type: O、ACTOR-1 宛）として再定義した（io.md v0.5→0.6）。旧 D-2 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。代替として O-3（修正後ノード）に `→FND-8` バックリファレンス辺を付与済み。

---

## FND-9: I-6「候補ファイルパス一覧」の名称が内容を表していない

<details><summary>⬡ FND-9 · v0.1</summary>

```yaml
id: FND-9
type: FND
labels: []
scheduled: ""
edges:
  - to: I-6
    ref_version: "0.6"
```
</details>

**深刻度**: INFO
**内容**: I-6 の名称「候補ファイルパス一覧」では「何の候補か」「どこから来たのか」が不明。実体は OS ファイルシステムのディレクトリ走査によって得た全 .md ファイルパスの列挙（trace_scope フィルタ適用前の生パス一覧）であり、その内容が名称から一切読み取れなかった。
**対応状況**: resolved
**対応内容**: I-6 名称を「ディレクトリ走査 .md ファイルパス一覧」に変更し、本文もの欄に「trace_scope フィルタ適用前の生のパス一覧」と明記した（io.md v0.5→0.6）。I-6 に `→FND-9` バックリファレンス辺を付与済み。

---

## FND-10: I-8「著作エージェント定義」の型分類誤り（I→P-7 内部）

<details><summary>⬡ FND-10 · v0.1</summary>

```yaml
id: FND-10
type: FND
labels: []
scheduled: ""
edges:
  - to: P-7
    ref_version: "0.6"
```
</details>

**深刻度**: ERROR
**内容**: I-8「著作エージェント定義」が I（系外アクタ発の入力）として分類されていたが、`.claude/agents/` 配下の定義ファイルは P-7 が呼び出されると自動ロードされるシステム内部プロンプトであり、外部からの入力ではない。「I＝系外」と「P-7 の内部定義」は定義上矛盾する。I として外に置くことで P-7 の実装詳細がグラフ上に漏れ出していた。
**対応状況**: resolved
**対応内容**: I-8 を io.md から削除し、著作エージェント定義を P-7 の内部定義として本文に組み込んだ（io.md v0.5→0.6、processes.md v0.5→0.6）。旧 I-8 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。代替として P-7（吸収先ノード）に `→FND-10` バックリファレンス辺を付与済み。

---

## FND-11: E-1 に入力辺が欠如（イベントには入力が必ず伴う）

<details><summary>⬡ FND-11 · v0.1</summary>

```yaml
id: FND-11
type: FND
labels: []
scheduled: ""
edges:
  - to: E-1
    ref_version: "0.5"
```
</details>

**深刻度**: WARNING
**内容**: E-1（点検要求）の edges に入力（I）への辺が存在しなかった。イベントの定義は「系外アクタが入力を持ち込んでシステムを起動し、プロセスがアクションを行い、レスポンスが生成される」であり、入力辺のないイベントはその定義を満たしていない。E-1 は仕様著者（ACTOR-1）または CI が I-1（ノードファイル群）を渡して spec-inspector を起動する事象であり、I-1 への辺が必要だった。
**対応状況**: resolved
**対応内容**: E-1 に `to: I-1, ref_version: "0.6"` 辺を追加し、スティミュラスに「**入力**」フィールドを明記した（events.md v0.4→0.5）。E-1 に `→FND-11` バックリファレンス辺を付与済み。
