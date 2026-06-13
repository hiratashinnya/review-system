---
version: "0.1.9"
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
  - to: P-1
    ref_version: "0.6"
  - to: FND-16
    ref_version: "0.1"
```
</details>

**深刻度**: ERROR
**内容**: ACTOR-3（spec-inspector）は外部 ACTOR として置かれているが、spec-inspector は本システム（検証 CLI）そのもの＝**系内処理**であり、既存の P-1〜P-4 と同一実体の二重表現である。out 辺は `→SR-4` のみで、E/I/O いずれからも被依存辺を受けず（`must_be_linked_from: ACTOR ← [E,I,O]` 違反・実質孤立に近い）、価値到達経路から浮いている。系外＝非アクタ（PR3/PR4）の原則に反する。
**対応状況**: resolved
**対応内容**: ACTOR-3 を削除し、spec-inspector を系内処理（P-1〜P-4）へ一本化した（actors.md v0.2→0.3）。ACTOR-3 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。ACTOR-3 の役割を吸収した P-1（ノード受付・パース）を forward 辺の張替え先とした（FND-16 対応）。P-1 に `→FND-1` バックリファレンスを付与済み。
**指摘時 ref_version**: ACTOR-3 "0.2"（actors.md v0.2 時点・当該ノードはその後削除済み）

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
  - to: E-2
    ref_version: "0.5"
  - to: DD-4
    ref_version: "0.1"
```
</details>

**深刻度**: WARNING
**内容**: events.md は E-1・E-3 のみで E-2 が欠番。E-1 のスティミュラス「仕様著者または CI」は CI 駆動を含意しており、CI 定期/フック起動が別事象として落ちている疑いがある。削除なら理由、別事象なら起票が必要。
**対応状況**: resolved
**対応内容**: E-3（著作要求）を E-2 へリネームして欠番を補正した（events.md・processes.md P-7 参照追従）。E-2 に `→FND-3` バックリファレンス辺を付与済み。forward 辺は指摘処置対象ノード E-2 を指すよう修正（FND-17 (d) 対応・DD-4 参照）。
**指摘時 ref_version**: E-1 "0.4"（events.md v0.4 時点に欠番として指摘。処置は E-3→E-2 リネームで、現在は E-2 が対象ノード）

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

## FND-6: I-1-1/I-1-2/I-1-3 の過分割の疑い

<details><summary>⬡ FND-6 · v0.1</summary>

```yaml
id: FND-6
type: FND
labels: []
scheduled: ""
edges:
  - to: I-1-1
    ref_version: "0.5"
```
</details>

**深刻度**: INFO
**内容**: suppress(I-1-1)/scheduled(I-1-2)/ref_version(I-1-3) を I-1（ノードファイル）と独立の入力に割っているが、いずれも著者がノードファイル内に書く値で、発生源・もの（ファイル）が同一である。PR1（もの＋発生源で分ける／使い道だけで割らない）に照らすと過分割の疑いがある。ただし各々が別 SPEC（SPEC-22/20/9）に紐づき追跡価値はある。
**対応状況**: resolved（2026-06-13）
**対応内容**: I-1-1/I-1-2/I-1-3 を I-1 の子ノード（親辺 `to: I-1`）として改名。階層を明示することで独立入力扱いの問題を解消。PEND-1 と連動してクローズ。

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

---

## FND-12: FR-1 の SPEC 分割が荒く YAML 不在・空集合・パース異常ケースが未定義

<details><summary>⬡ FND-12 · v0.1</summary>

```yaml
id: FND-12
type: FND
labels: []
scheduled: ""
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**深刻度**: WARNING
**内容**: FR-1（ノードグラフの構造化表現）配下の SPEC は正常パース（SPEC-1）と崩れた記法（旧 SPEC-2）のみで、(a) in-graph 0 件の空集合、(b) ⬡ マーカー直後に YAML ブロックが無い、(c) id 欠如、(d) type 欠如、(e) 辺の ref_version 欠如、といった等価分割クラスが未定義だった。パース段階の異常系（fail-close 対象）が仕様化されておらず、テスト設計の網羅軸が欠落していた。
**対応状況**: resolved
**対応内容**: パース検証 RULE-023〜027 を新設（docs/doc-system/05-verification.md 段階0・config 反映）。FR-1 配下に SPEC-31（empty・in-graph 0 件）・SPEC-32（RULE-024）・SPEC-33（RULE-025）・SPEC-34（RULE-026）・SPEC-35（RULE-027）を追加し、SPEC-2 を RULE-023 限定に書き直した（spec.md v0.3.0→0.3.1）。FR-1 に `→FND-12` バックリファレンス辺を付与済み（reconciliation が付与）。

---

## FND-13: condition 語彙に空集合クラス（empty）が欠落し null/ゼロ件を boundary/normal に混入していた

<details><summary>⬡ FND-13 · v0.1</summary>

```yaml
id: FND-13
type: FND
labels: []
scheduled: ""
edges:
  - to: SPEC-31
    ref_version: "0.3"
```
</details>

**深刻度**: WARNING
**内容**: condition 語彙が normal/boundary/failure/error の4語のみで、空集合・ゼロ件・null・未設定（in-graph 0 件など）を表す独立クラスが無かった。これらを normal や boundary に混ぜると等価分割が崩れ、テスト設計上の網羅穴になる。SPEC-31（in-graph 0 件）を著作する際にこの語彙不足が顕在化した。
**対応状況**: resolved
**対応内容**: `config.yaml` の condition_vocab に `empty` を追加し5語化（normal/boundary/empty/failure/error）、各語の説明コメントを追記。語彙を列挙する全箇所（spec.md 冒頭ガイド・04-notation・07-authoring-guide・02-meta-schema DD-010・01-document-items・spec-author/test-strategy/io-event-ledger）を5語へ更新。SPEC-31 が empty を使用。SPEC-31 に `→FND-13` バックリファレンス辺を付与済み（reconciliation が付与）。なお発生源の `config.yaml` は out-of-graph（trace_scope.exclude）のためノードを持たず、in-graph アンカーとして SPEC-31 に紐づけた。

---

## FND-14: SPEC 本文がテスタブルでない（定量・一意・出力フォーマット欠如）

<details><summary>⬡ FND-14 · v0.1</summary>

```yaml
id: FND-14
type: FND
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3"
  - to: SPEC-2
    ref_version: "0.3"
  - to: SPEC-26
    ref_version: "0.3"
  - to: SPEC-27
    ref_version: "0.3"
```
</details>

**深刻度**: WARNING
**内容**: 既存 SPEC-1/2/26/27 の本文が「壊れていて抽出できない」「正しく著作できる」等の曖昧表現に留まり、(1) 定量的前提、(2) 一意なトリガ、(3) 出力フォーマット（`{SEVERITY}|{file}:{line}|{RULE-NNN}|{node-id}|{message}`）、(4) 終了コード、(5) 具体例、が欠けていた。2人が同じ本文から同一テストを書ける水準（テスタビリティ）を満たさず、仕様としての体を成していなかった。
**対応状況**: resolved
**対応内容**: 「SPEC テスタビリティ基準（必須チェックリスト8項目）」を docs/doc-system/07-authoring-guide.md に焼き込み、SPEC-1/2/26/27 を前提条件/入力・トリガ/期待動作/例の4項目・定量・出力フォーマット明記で書き直した（spec.md v0.3.0→0.3.1）。SPEC-1/2/26/27 にそれぞれ `→FND-14` バックリファレンス辺を付与済み（reconciliation が付与）。

---

## FND-15: FR-11「著作支援」が過積載でテンプレ/エージェント/ワークフロー/伝搬編集/エラー系が未分化

<details><summary>⬡ FND-15 · v0.1</summary>

```yaml
id: FND-15
type: FND
labels: []
scheduled: ""
edges:
  - to: FR-11
    ref_version: "0.2"
```
</details>

**深刻度**: WARNING
**内容**: FR-11 が「テンプレート提供」と「著作エージェントへの規約内包」を1 FR に束ね、さらに層単位ワークフロー・伝搬編集支援・テンプレート品質のエラー系が未仕様だった。`suppress: [RULE-018]` で異常系不在を宣言しており、著作支援の失敗系（テンプレ欠損・著作出力の不備）が機械検証から外れていた。1 FR の責務過積載で価値の分解が不十分（粒度過大）。
**対応状況**: resolved
**対応内容**: FR-11 をテンプレートによる著作品質保証に限定（v0.3→0.4・suppress 削除）、著作エージェント＋層ワークフローを FR-13 として、伝搬編集支援（post-MVP）を FR-14 として分離（fr.md v0.2.1→0.2.2）。失敗系 SPEC-36（テンプレ必須欠如）・SPEC-39（著作出力 id 欠如）と正常系 SPEC-38・SPEC-40 を追加。FR-11 に `→FND-15` バックリファレンス辺を付与済み（reconciliation が付与）。

---

## FND-16: FND-1 の forward 辺が削除済み ACTOR-3 を指して dangling（RULE-007 ERROR）

<details><summary>⬡ FND-16 · v0.1</summary>

```yaml
id: FND-16
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-1
    ref_version: "0.1"
```
</details>

**深刻度**: ERROR
**内容**: FND-1（ACTOR-3 系境界誤りの指摘・resolved）が依存辺 `to: ACTOR-3` を保持しているが、ACTOR-3 は FND-1 の処置で削除済みであり、存在しない ID を参照している（RULE-007・always_error＝stage/suppress に関わらず発火）。FND は対象要素への辺が1本以上必須（RULE-006: FND→any）だが、唯一の対象が消滅したため forward 辺が宙に浮いている。FND-1 本文には「削除済みのため付与先なし」と記載済みだが、forward 辺自体は残置されダングリングになっている。
**対応状況**: resolved
**対応内容**: FND-1 の forward 辺を `to: ACTOR-3` から `to: P-1（processes.md v0.6）` に張替え。P-1（ノード受付・パース）は ACTOR-3 の系内処理の役割を担う代表ノード。P-1 に `→FND-1` バックリファレンスを付与済み。FND-1 に `→FND-16` バックリファレンスを付与済み（dangling 修正の根拠 FND として記録）。

---

## FND-17: 分析層の版上げに伴う ref_version ドリフト群（記録・義務辺含む・RULE-004 WARNING）

<details><summary>⬡ FND-17 · v0.1</summary>

```yaml
id: FND-17
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: VERIFY-1
    ref_version: "0.1"
```
</details>

**深刻度**: WARNING
**内容**: 分析層ファイルの版上げに下流の ref_version 更新が追随しておらず RULE-004 ドリフトが多発。
- (a) `01-actors.md` が 0.2→0.3（ACTOR-3 削除の x.y 上昇）したが、流入辺 E-1→ACTOR-1・E-2→ACTOR-1・O-1→ACTOR-2・O-2→ACTOR-2・VERIFY-1→ACTOR-1 が "0.2" のまま。
- (b) VERIFY-1 の I-1("0.4"→現0.6)・P-1("0.4"→現0.6)・E-1("0.4"→現0.5) が陳腐化。
- (c) 解消済み FND-2→P-2("0.5"→0.6)・FND-3→E-1("0.4"→0.5)・FND-4→P-3("0.5"→0.6)、義務辺 PEND-1→I-1-1("0.5"→0.6) がドリフト。
- (d) 付随：FND-3 の forward 辺が E-1 を指すが、当該指摘の処置（E-3→E-2 リネーム）の back-ref は E-2 に付与されており、forward/back の対象ノードが不一致（FND-3 は本来 E-2 を指すべき疑い）。

**対応状況**: resolved
**対応内容**: DD-4（decisions.md）として昇格し推奨案を実施。「生きた」依存辺（E-1/E-2→ACTOR-1・O-1/O-2→ACTOR-2 の ref_version "0.2"→"0.3"、FND-3 forward の E-1→E-2＋"0.5"、PEND-1→I-1-1 の "0.5"→"0.6"）を一括更新済み。凍結記録（VERIFY-1・解消済み FND-2/FND-4）は DD-2 決定（suppress[RULE-004]・再検証シグナル）に委ねる。処置対象ノードに `→DD-4` バックリファレンス付与済み。

---

## FND-18: I/O ノードのフォーマット定義が非公式散文にとどまり SPEC として機械検証不可

<details><summary>⬡ FND-18 · v0.1</summary>

```yaml
id: FND-18
type: FND
labels: []
scheduled: ""
edges:
  - to: I-1
    ref_version: "0.6"
  - to: FR-1
    ref_version: "0.2"
```
</details>

**深刻度**: WARNING
**内容**: I/O ノード（I-1〜I-7・O-1〜O-3）の本文 `**形式**:` フィールドはすべて非公式な散文記述にとどまっており、SPEC ノードとして機械検証可能なフォーマット定義が存在しない。

具体的な欠落:
- **I-1 入力フォーマット（最重要）**: ノードファイルの有効な YAML frontmatter に含まれる全フィールド（`id`・`type`・`labels`・`scheduled`・`suppress`・`edges`・`condition`・`result`・`log_ref`）の型・必須/任意・値制約を正式定義する SPEC がない。SPEC-1/2・SPEC-31〜35 はパース動作とエラーケースをカバーするが、完全フィールドスキーマは未仕様。02-meta-schema.md が事実上の定義源だが out-of-graph（trace_scope 除外）であり RULE 対象外。
- **O-2 出力フォーマット**: SPEC-14 はカバレッジ点検の内容を規定するが、カバレッジテーブルの具体的な出力形式（列名・行フォーマット・ソートキー）が未定義。
- **I-7 テンプレートフォーマット**: SPEC-26 は著作プロセス（P-7 が I-7 を参照すること）を規定するが、テンプレートファイル自体が満たすべき構造（型・必須セクション・プレースホルダ形式）が未仕様。

影響: フォーマット違反のノードファイルやテンプレートを spec-inspector が検出できない。仕様の唯一ソースが out-of-graph ドキュメントに依存し続ける。
**対応状況**: resolved（重複不可方針で再処置・2026-06-13）

**経緯①（初回処置を差し戻し）**: 初回処置で SPEC-41（I-1 完全スキーマ）・SPEC-42（O-2 カバレッジ出力）・SPEC-43（I-7 テンプレート構造）を著作したが、オーナーレビューで**テスタブルな粒度に達していない**として差し戻し（spec.md v0.3.3 で 3 SPEC 撤去）。粒度違反:
- **SPEC-41**: 「必須フィールド存在」「型チェック4種」「未知キー→WARNING」を 1 ノードに束ね・normal/failure 混在。
- **SPEC-43**: 「id/type/edges/型別必須フィールド」を束ね・normal/error 混在。
- **SPEC-42**: ヘッダ/行/ソート/gap を束ね・gap は既存 SPEC との重複疑い。

**経緯②（重複不可方針で再処置・採用）**: 既存 SPEC を精査し、**重複を作らず真の欠落のみ**を 1 アサーション 1 SPEC で再著作（spec.md v0.3.4）:
- **I-7 テンプレート構造 → 新規ゼロ（重複回避）**: 既存 **SPEC-26**（FR-11・normal・テンプレが id/type/labels/scheduled/edges/本文4項目を含む）＋ **SPEC-36**（FR-11・failure・テンプレ由来必須欠如→RULE-025/026）が既に充足。当初の「I-7 未仕様」判断は誤りで、既存カバレッジを見落としていた。新規 SPEC は起票しない。
- **I-1 完全スキーマ → SPEC-52（FR-1・normal）＋ SPEC-53（FR-1・failure・RULE-028）**: id/type 欠如（SPEC-33/34）・ref_version 欠如（SPEC-35）は既出のため重複回避し、**残る共通必須フィールド `labels`/`scheduled`/`edges` の存在と型**を新 RULE-028 で検証。SPEC-52 が完全スキーマ適合（normal）、SPEC-53 が型不正・欠如検出（failure）。RULE-028 を `docs/doc-system/05-verification.md` 段階0（パース検証・ノード単位 fail-close）に追加。
- **O-2 出力フォーマット → SPEC-14-1（SPEC-14 の -N 分割・normal）**: 親 SPEC-14（FR-6・カバレッジレポート生成）の出力フォーマットを精緻化（ヘッダ列名・行フォーマット・FR-id 昇順ソート）。gap 出力は SPEC-14 本体／RULE-017/018 の責務として**重複回避**。当初 FR-3 配下に置こうとしたが、カバレッジの正当な親は FR-6（SPEC-14）と判明。

**処置対象ノードへの backref**: I-1・FR-1（指摘対象）・SPEC-14（O-2 フォーマット精緻化先）に `→FND-18` を付与。

**指摘時 ref_version**: I-1 "0.6"（io.md v0.6.2 時点）、FR-1 "0.2"（fr.md v0.2.2 時点）

---

## FND-19: P-7「ノード著作プロセス」の単一責務違反（著作＋調停の2活動内包）

<details><summary>⬡ FND-19 · v0.1</summary>

```yaml
id: FND-19
type: FND
labels: []
scheduled: ""
edges:
  - to: P-7
    ref_version: "0.6"
```
</details>

**深刻度**: WARNING
**内容**: P-7「ノード著作プロセス」が次の2活動を1プロセスに内包している。
- (1) **著作**: 仕様著者（ACTOR-1）＋著作エージェントが `tmp/<sprint>/<id>.md` に草案を出力する活動（SPEC-38・E-2 トリガ）。
- (2) **調停**: reconciliation エージェントが tmp を検証し本ファイルへ転記し O-3 を生成する活動（SPEC-39）。

別アクタ（著作エージェント vs reconciliation エージェント）・別段階（草案 vs 確定）であり、DFD レベリング上の単一責務違反（PR9）。対応 SPEC-38/39 も別責務に対応しており、1プロセスに束ねるのは粒度過大。
**対応状況**: resolved
**対応内容**: DFD レベリングで P-7 を **P-7-1**（著作・tmp 出力・SPEC-38）と **P-7-2**（調停・本ファイル反映・SPEC-39）に分解した。O-3 の生成元辺を P-7→P-7-2 に張替え。P-7 に `→FND-19` バックリファレンス辺を付与済み（processes.md v0.6.3→0.6.4・io.md v0.6.5→0.6.6）。
**指摘時 ref_version**: P-7 "0.6"（processes.md v0.6.3 時点）

---

## FND-20: P-1「受付・パース」にパース段検証（RULE-023〜028）の責務記述がなく対応 SPEC が無主

<details><summary>⬡ FND-20 · v0.1</summary>

```yaml
id: FND-20
type: FND
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.6"
```
</details>

**深刻度**: WARNING
**内容**: P-1「受付・パース」は構造化ノードセットを生成するが、本文の責務記述にパース段検証（RULE-023〜028）が含まれていない。対応する SPEC-2（RULE-023）・SPEC-32（RULE-024）・SPEC-33（RULE-025）・SPEC-34（RULE-026）・SPEC-35（RULE-027）・SPEC-36（テンプレ由来 RULE-025/026）・SPEC-52（スキーマ適合）・SPEC-53（RULE-028）が、どの P からも参照されない無主状態であり、FR/SPEC の裏付けを持つ機能が分析層のプロセスに接続されていない＝価値経路の穴（PR6）。P-1 はパース処理そのものを担うため、これらパース段検証は P-1 の単一責務（パース段処理）に含めるのが妥当である。
**対応状況**: resolved
**対応内容**: P-1 の責務記述を「パース＋パース段検証（RULE-023〜028）」に明確化し、SPEC-2/32/33/34/35/36/52/53 への依存辺を P-1 に追加した（P-2-2 が複数 RULE を1責務で持つのと同様、パース段処理は単一責務として保持し分解しない）。SPEC-36（テンプレ由来の必須欠如）はその期待動作が RULE-025/026 の検出報告であり、検出主体は P-1（パース段）であるため P-1 に接続（VERIFY-3 後の spec-inspector 点検 G1 を反映）。P-1 に `→FND-20` バックリファレンス辺を付与済み（processes.md v0.6.3→0.6.4）。なお SPEC-31（empty・in-graph 0 件）はパースではなく in-graph 集合決定/オーケストレーションの責務のため P-1 には含めず、別途 P-6/orchestration の論点として残す。
**指摘時 ref_version**: P-1 "0.6"（processes.md v0.6.3 時点）
