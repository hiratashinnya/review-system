# 指摘・Finding — doc-system ドッグフーディング（要件〜分析層）

> **型**: FND ／ **必須**: 指摘対象要素への依存辺が1本以上（RULE-006 config: `must_link_to: FND → any`）
> 無名依存辺のみ（`kind`/`status` なし・`to` は単数・全辺に `ref_version` 必須）。
> 要件フェーズのため、指摘対象ノード自体は未修正（オーナー判断待ちの記録）。

---

## FND-1: ACTOR-3（spec-inspector）の系境界誤り（被依存辺ゼロ）

<details><summary>⬡ FND-1 · v0.1.0</summary>

```yaml
id: FND-1
type: FND
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.2.0"
  - to: FND-16
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: ACTOR-3（spec-inspector）は外部 ACTOR として置かれているが、spec-inspector は本システム（検証 CLI）そのもの＝**系内処理**であり、既存の P-1〜P-4 と同一実体の二重表現である。out 辺は `→SR-4` のみで、E/I/O いずれからも被依存辺を受けず（`must_be_linked_from: ACTOR ← [E,I,O]` 違反・実質孤立に近い）、価値到達経路から浮いている。系外＝非アクタ（PR3/PR4）の原則に反する。
**対応状況**: resolved
**対応内容**: ACTOR-3 を削除し、spec-inspector を系内処理（P-1〜P-4）へ一本化した（actors.md v0.2→0.3）。ACTOR-3 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。ACTOR-3 の役割を吸収した P-1（ノード受付・パース）を forward 辺の張替え先とした（FND-16 対応）。P-1 に `→FND-1` バックリファレンスを付与済み。
**指摘時 ref_version**: ACTOR-3 "0.2"（actors.md v0.2 時点・当該ノードはその後削除済み）

---

## FND-2: P-2「RULE 検査」の単一責務違反（粒度過大）

<details><summary>⬡ FND-2 · v0.1.0</summary>

```yaml
id: FND-2
type: FND
labels: []
scheduled: ""
edges:
  - to: P-2
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: P-2 が構造完結性（RULE-005〜008）・ドリフト（RULE-001/002/004/022）・カバレッジ（RULE-016〜019）・検証層（RULE-006/020/021）の全 RULE 群を1プロセスに内包している。対応 SPEC が SPEC-5〜23 と多数に分かれているのに、P-2 だけがそれらを束ねており、DFD レベリング上の単一責務の疑いがある。
**対応状況**: resolved
**対応内容**: DFD レベリングにより P-2 を P-2-1（ドリフト・義務辺）・P-2-2（構造完結性）・P-2-3（カバレッジ属性）・P-2-4（検証層完結性）の4子プロセスへ分解した（processes.md v0.4→0.5）。P-2 に `→FND-2` バックリファレンス辺を付与済み。

---

## FND-3: events.md の E-2 欠番

<details><summary>⬡ FND-3 · v0.1.0</summary>

```yaml
id: FND-3
type: FND
labels: []
scheduled: ""
edges:
  - to: E-2
    ref_version: "0.3.0"
  - to: DD-4
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: events.md は E-1・E-3 のみで E-2 が欠番。E-1 のスティミュラス「仕様著者または CI」は CI 駆動を含意しており、CI 定期/フック起動が別事象として落ちている疑いがある。削除なら理由、別事象なら起票が必要。
**対応状況**: resolved
**対応内容**: E-3（著作要求）を E-2 へリネームして欠番を補正した（events.md・processes.md P-7 参照追従）。E-2 に `→FND-3` バックリファレンス辺を付与済み。forward 辺は指摘処置対象ノード E-2 を指すよう修正（FND-17 (d) 対応・DD-4 参照）。
**指摘時 ref_version**: E-1 "0.4"（events.md v0.4 時点に欠番として指摘。処置は E-3→E-2 リネームで、現在は E-2 が対象ノード）

---

## FND-4: カバレッジ点検（グラフ網羅性）の上流 SPEC 欠落

<details><summary>⬡ FND-4 · v0.1.0</summary>

```yaml
id: FND-4
type: FND
labels: []
scheduled: ""
edges:
  - to: P-3
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: P-3「カバレッジ点検」本文は「孤児ノード・未駆動出力・未定義反応」（グラフ網羅性点検）と「SPEC×condition×TD」の2系統を担うが、P-3 の依存先は SPEC-14 のみである。前者のグラフ網羅性点検に対応する SPEC が spec.md に存在せず、FR/SPEC の裏付けがない機能が分析層に出現している＝価値経路の上流欠落（PR6）。
**対応状況**: resolved
**対応内容**: SPEC-29（正常系）・SPEC-30（接続漏れ検出）を FR-3 配下に新設し、P-3 を P-3-1（グラフ網羅性）・P-3-2（仕様カバレッジ計測）に分解した（spec.md・processes.md v0.5）。P-3・SPEC-29・SPEC-30 に `→FND-4` バックリファレンス辺を付与済み。

---

## FND-5: FR-6 本文が廃止 RULE-015 を生きた番号として参照

<details><summary>⬡ FND-5 · v0.1.0</summary>

```yaml
id: FND-5
type: FND
labels: []
scheduled: ""
edges:
  - to: FR-6
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: FR-6 本文は「TD の verifies 欠如（RULE-015）」を現役ルールとして記載するが、正本では RULE-015 は廃止され `must_be_linked_from: SPEC←[TD]`（RULE-006）に吸収済みである（docs/doc-system/05-verification.md L74・spec.md SPEC-15-1 は正しく「旧 RULE-015」と記述）。FR-6 のみ記述が旧モデルに取り残されている。
**対応状況**: resolved
**対応内容**: FR-6 本文の「TD の verifies 欠如（RULE-015）」を「SPEC への TD 被依存辺欠如（`must_be_linked_from: SPEC←[TD]`・RULE-006・旧 RULE-015）」へ修正した（fr.md）。FR-6 に `→FND-5` バックリファレンス辺を付与済み。

---

## FND-6: I-1-1/I-1-2/I-1-3 の過分割の疑い

<details><summary>⬡ FND-6 · v0.2.0</summary>

```yaml
id: FND-6
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: D-18
    ref_version: "0.1.0"
  - to: DD-12
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: suppress(I-1-1)/scheduled(I-1-2)/ref_version(I-1-3) を I-1（ノードファイル）と独立の入力に割っているが、いずれも著者がノードファイル内に書く値で、発生源・もの（ファイル）が同一である。PR1（もの＋発生源で分ける／使い道だけで割らない）に照らすと過分割の疑いがある。ただし各々が別 SPEC（SPEC-22/20/9）に紐づき追跡価値はある。

**対応状況**: resolved（2026-06-13 初回解消・2026-06-15 DD-12 退役で再解消・supersede）

**対応内容（経緯①・初回解消 2026-06-13）**: I-1-1/I-1-2/I-1-3 を I-1 の子ノード（親辺 `to: I-1`）として改名。階層を明示することで独立入力扱いの問題を解消。PEND-1 と連動してクローズ。

**対応内容（経緯②・DD-12 退役による supersede 2026-06-15）**: 分析層全面見直し（DD-12・オーナー承認）で、I-1-1/I-1-2/I-1-3 を「I-1 の子ノード」として残す初回解消からさらに踏み込み、**3 ノードを退役**した（系外入力ではなく D-4 のパース派生属性＝PR1/PR9 違反の根本是正・初回解消はノード自体を残したため過分割の疑いを完全には消せていなかった）。退役後、各フィールドは分析層の射影スライスへ吸収される：
- **I-1-1 suppress → D-18（属性検査ビュー）の suppress 属性**（io.md「suppress は D-18 の属性として一元保持し P-2-5 へ渡す」）。
- **I-1-2 scheduled → D-18 の scheduled 属性**（＋D-9 フェーズ・ステージ状態との突合で発火判定）。
- **I-1-3 ref_version → D-19（決定辺ビュー）の edges.ref_version スライス**。

本 FND の forward 辺は、退役で消える `to: I-1-1` から、suppress の吸収先である **`to: D-18` へ repoint** した（指摘の主題＝suppress の過分割の現在の所在が D-18 の属性であるため）。あわせて退役を決定した上位決定 **`to: DD-12`** への辺を張り、本 FND が DD-12 によって supersede（さらに踏み込んで解消）された関係を辺でも追跡可能にした。I-1-1/I-1-2/I-1-3 は退役済み（再利用しない＝DD-7）のため、退役ノード自体への辺は撤去した。

**指摘時 ref_version**: I-1-1 "0.1"（io.md・I-1-1 ノードバッジ v0.1 時点＝退役前の初回指摘対象。退役後は付与先消滅のため D-18 "0.1" へ repoint）

> **注（DD-3 履歴保全）**: 元の指摘対象 I-1-1（およびその同根 I-1-2/I-1-3）は v0.1 時点のノードであり、本 FND はその版を指摘した。退役（DD-12）により I-1-1 への辺が dangling になるため吸収先 D-18 へ repoint したが、上記「指摘時 ref_version」に元の対象・版を凍結記録し provenance を保持する。

---

## FND-7: E-2 スティミュラスが「新規ノード著作」のみで既存ノード改訂を含まない

<details><summary>⬡ FND-7 · v0.1.0</summary>

```yaml
id: FND-7
type: FND
labels: []
scheduled: ""
edges:
  - to: E-2
    ref_version: "0.3.0"
```
</details>

**深刻度**: WARNING
**内容**: E-2（著作要求）のスティミュラスが「仕様著者（ACTOR-1）が**新規ノード著作**を決定し」と記述されており、既存ノードの内容変更・辺追加・バージョンバンプといった改訂操作が同じ著作フロー（P-7 → reconciliation）を通るにもかかわらずイベント定義から漏れていた。E は系外アクタが入力を持ち込んで起こす事象であり、新規作成と既存改訂は同一事象のバリアントとして定義すべきだった。
**対応状況**: resolved
**対応内容**: E-2 スティミュラスを「ノード著作（新規作成または既存改訂）を決定し」へ修正した（events.md v0.4→0.5）。E-2 に `→FND-7` バックリファレンス辺を付与済み。

---

## FND-8: D-2「著作済みノードファイル」の型分類誤り（D→O）

<details><summary>⬡ FND-8 · v0.1.0</summary>

```yaml
id: FND-8
type: FND
labels: []
scheduled: ""
edges:
  - to: O-3
    ref_version: "0.2.0"
```
</details>

**深刻度**: ERROR
**内容**: 旧 D-2「著作済みノードファイル」が D（内部データフロー・系外へ出ない）として分類されていた。しかしイベントの定義は「系外アクタが入力を持ち込み、プロセスがアクションを行い、外部アクタへのレスポンスが生成される」であり、E-2（著作要求）のレスポンスは O 型（系外アクタ宛の出力）でなければならない。D 型では O→ACTOR 辺が持てず ACTOR-1 への価値到達が表現できなかった。
**対応状況**: resolved
**対応内容**: D-2 を削除し O-3（type: O、ACTOR-1 宛）として再定義した（io.md v0.5→0.6）。旧 D-2 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。代替として O-3（修正後ノード）に `→FND-8` バックリファレンス辺を付与済み。

---

## FND-9: I-6「候補ファイルパス一覧」の名称が内容を表していない

<details><summary>⬡ FND-9 · v0.1.0</summary>

```yaml
id: FND-9
type: FND
labels: []
scheduled: ""
edges:
  - to: I-6
    ref_version: "0.3.0"
```
</details>

**深刻度**: INFO
**内容**: I-6 の名称「候補ファイルパス一覧」では「何の候補か」「どこから来たのか」が不明。実体は OS ファイルシステムのディレクトリ走査によって得た全 .md ファイルパスの列挙（trace_scope フィルタ適用前の生パス一覧）であり、その内容が名称から一切読み取れなかった。
**対応状況**: resolved
**対応内容**: I-6 名称を「ディレクトリ走査 .md ファイルパス一覧」に変更し、本文もの欄に「trace_scope フィルタ適用前の生のパス一覧」と明記した（io.md v0.5→0.6）。I-6 に `→FND-9` バックリファレンス辺を付与済み。

---

## FND-10: I-8「著作エージェント定義」の型分類誤り（I→P-7 内部）

<details><summary>⬡ FND-10 · v0.1.0</summary>

```yaml
id: FND-10
type: FND
labels: []
scheduled: ""
edges:
  - to: P-7
    ref_version: "0.4.0"
```
</details>

**深刻度**: ERROR
**内容**: I-8「著作エージェント定義」が I（系外アクタ発の入力）として分類されていたが、`.claude/agents/` 配下の定義ファイルは P-7 が呼び出されると自動ロードされるシステム内部プロンプトであり、外部からの入力ではない。「I＝系外」と「P-7 の内部定義」は定義上矛盾する。I として外に置くことで P-7 の実装詳細がグラフ上に漏れ出していた。
**対応状況**: resolved
**対応内容**: I-8 を io.md から削除し、著作エージェント定義を P-7 の内部定義として本文に組み込んだ（io.md v0.5→0.6、processes.md v0.5→0.6）。旧 I-8 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。代替として P-7（吸収先ノード）に `→FND-10` バックリファレンス辺を付与済み。

---

## FND-11: E-1 に入力辺が欠如（イベントには入力が必ず伴う）

<details><summary>⬡ FND-11 · v0.1.0</summary>

```yaml
id: FND-11
type: FND
labels: []
scheduled: ""
edges:
  - to: E-1
    ref_version: "0.5.0"
```
</details>

**深刻度**: WARNING
**内容**: E-1（点検要求）の edges に入力（I）への辺が存在しなかった。イベントの定義は「系外アクタが入力を持ち込んでシステムを起動し、プロセスがアクションを行い、レスポンスが生成される」であり、入力辺のないイベントはその定義を満たしていない。E-1 は仕様著者（ACTOR-1）または CI が I-1（ノードファイル群）を渡して spec-inspector を起動する事象であり、I-1 への辺が必要だった。
**対応状況**: resolved
**対応内容**: E-1 に `to: I-1, ref_version: "0.6.0"` 辺を追加し、スティミュラスに「**入力**」フィールドを明記した（events.md v0.4→0.5）。E-1 に `→FND-11` バックリファレンス辺を付与済み。

---

## FND-12: FR-1 の SPEC 分割が荒く YAML 不在・空集合・パース異常ケースが未定義

<details><summary>⬡ FND-12 · v0.1.0</summary>

```yaml
id: FND-12
type: FND
labels: []
scheduled: ""
edges:
  - to: FR-1
    ref_version: "0.3.0"
```
</details>

**深刻度**: WARNING
**内容**: FR-1（ノードグラフの構造化表現）配下の SPEC は正常パース（SPEC-1）と崩れた記法（旧 SPEC-2）のみで、(a) in-graph 0 件の空集合、(b) ⬡ マーカー直後に YAML ブロックが無い、(c) id 欠如、(d) type 欠如、(e) 辺の ref_version 欠如、といった等価分割クラスが未定義だった。パース段階の異常系（fail-close 対象）が仕様化されておらず、テスト設計の網羅軸が欠落していた。
**対応状況**: resolved
**対応内容**: パース検証 RULE-023〜027 を新設（docs/doc-system/05-verification.md 段階0・config 反映）。FR-1 配下に SPEC-31（empty・in-graph 0 件）・SPEC-32（RULE-024）・SPEC-33（RULE-025）・SPEC-34（RULE-026）・SPEC-35（RULE-027）を追加し、SPEC-2 を RULE-023 限定に書き直した（spec.md v0.3.0→0.3.1）。FR-1 に `→FND-12` バックリファレンス辺を付与済み（reconciliation が付与）。

---

## FND-13: condition 語彙に空集合クラス（empty）が欠落し null/ゼロ件を boundary/normal に混入していた

<details><summary>⬡ FND-13 · v0.1.0</summary>

```yaml
id: FND-13
type: FND
labels: []
scheduled: ""
edges:
  - to: SPEC-31
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: condition 語彙が normal/boundary/failure/error の4語のみで、空集合・ゼロ件・null・未設定（in-graph 0 件など）を表す独立クラスが無かった。これらを normal や boundary に混ぜると等価分割が崩れ、テスト設計上の網羅穴になる。SPEC-31（in-graph 0 件）を著作する際にこの語彙不足が顕在化した。
**対応状況**: resolved
**対応内容**: `config.yaml` の condition_vocab に `empty` を追加し5語化（normal/boundary/empty/failure/error）、各語の説明コメントを追記。語彙を列挙する全箇所（spec.md 冒頭ガイド・04-notation・07-authoring-guide・02-meta-schema DD-010・01-document-items・spec-author/test-strategy/io-event-ledger）を5語へ更新。SPEC-31 が empty を使用。SPEC-31 に `→FND-13` バックリファレンス辺を付与済み（reconciliation が付与）。なお発生源の `config.yaml` は out-of-graph（trace_scope.exclude）のためノードを持たず、in-graph アンカーとして SPEC-31 に紐づけた。

---

## FND-14: SPEC 本文がテスタブルでない（定量・一意・出力フォーマット欠如）

<details><summary>⬡ FND-14 · v0.1.0</summary>

```yaml
id: FND-14
type: FND
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3.0"
  - to: SPEC-2
    ref_version: "0.3.0"
  - to: SPEC-26
    ref_version: "0.3.0"
  - to: SPEC-27
    ref_version: "0.3.0"
```
</details>

**深刻度**: WARNING
**内容**: 既存 SPEC-1/2/26/27 の本文が「壊れていて抽出できない」「正しく著作できる」等の曖昧表現に留まり、(1) 定量的前提、(2) 一意なトリガ、(3) 出力フォーマット（`{SEVERITY}|{file}:{line}|{RULE-NNN}|{node-id}|{message}`）、(4) 終了コード、(5) 具体例、が欠けていた。2人が同じ本文から同一テストを書ける水準（テスタビリティ）を満たさず、仕様としての体を成していなかった。
**対応状況**: resolved
**対応内容**: 「SPEC テスタビリティ基準（必須チェックリスト8項目）」を docs/doc-system/07-authoring-guide.md に焼き込み、SPEC-1/2/26/27 を前提条件/入力・トリガ/期待動作/例の4項目・定量・出力フォーマット明記で書き直した（spec.md v0.3.0→0.3.1）。SPEC-1/2/26/27 にそれぞれ `→FND-14` バックリファレンス辺を付与済み（reconciliation が付与）。

---

## FND-15: FR-11「著作支援」が過積載でテンプレ/エージェント/ワークフロー/伝搬編集/エラー系が未分化

<details><summary>⬡ FND-15 · v0.1.0</summary>

```yaml
id: FND-15
type: FND
labels: []
scheduled: ""
edges:
  - to: FR-11
    ref_version: "0.4.0"
```
</details>

**深刻度**: WARNING
**内容**: FR-11 が「テンプレート提供」と「著作エージェントへの規約内包」を1 FR に束ね、さらに層単位ワークフロー・伝搬編集支援・テンプレート品質のエラー系が未仕様だった。`suppress: [RULE-018]` で異常系不在を宣言しており、著作支援の失敗系（テンプレ欠損・著作出力の不備）が機械検証から外れていた。1 FR の責務過積載で価値の分解が不十分（粒度過大）。
**対応状況**: resolved
**対応内容**: FR-11 をテンプレートによる著作品質保証に限定（v0.3→0.4・suppress 削除）、著作エージェント＋層ワークフローを FR-13 として、伝搬編集支援（post-MVP）を FR-14 として分離（fr.md v0.2.1→0.2.2）。失敗系 SPEC-36（テンプレ必須欠如）・SPEC-39（著作出力 id 欠如）と正常系 SPEC-38・SPEC-40 を追加。FR-11 に `→FND-15` バックリファレンス辺を付与済み（reconciliation が付与）。

---

## FND-16: FND-1 の forward 辺が削除済み ACTOR-3 を指して dangling（RULE-007 ERROR）

<details><summary>⬡ FND-16 · v0.1.0</summary>

```yaml
id: FND-16
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: FND-1（ACTOR-3 系境界誤りの指摘・resolved）が依存辺 `to: ACTOR-3` を保持しているが、ACTOR-3 は FND-1 の処置で削除済みであり、存在しない ID を参照している（RULE-007・always_error＝stage/suppress に関わらず発火）。FND は対象要素への辺が1本以上必須（RULE-006: FND→any）だが、唯一の対象が消滅したため forward 辺が宙に浮いている。FND-1 本文には「削除済みのため付与先なし」と記載済みだが、forward 辺自体は残置されダングリングになっている。
**対応状況**: resolved
**対応内容**: FND-1 の forward 辺を `to: ACTOR-3` から `to: P-1（processes.md v0.6）` に張替え。P-1（ノード受付・パース）は ACTOR-3 の系内処理の役割を担う代表ノード。P-1 に `→FND-1` バックリファレンスを付与済み。FND-1 に `→FND-16` バックリファレンスを付与済み（dangling 修正の根拠 FND として記録）。

---

## FND-17: 分析層の版上げに伴う ref_version ドリフト群（記録・義務辺含む・RULE-004 WARNING）

<details><summary>⬡ FND-17 · v0.1.0</summary>

```yaml
id: FND-17
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: VERIFY-1
    ref_version: "0.1.0"
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

<details><summary>⬡ FND-18 · v0.1.0</summary>

```yaml
id: FND-18
type: FND
labels: []
scheduled: ""
edges:
  - to: I-1
    ref_version: "0.1.0"
  - to: FR-1
    ref_version: "0.3.0"
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

<details><summary>⬡ FND-19 · v0.1.0</summary>

```yaml
id: FND-19
type: FND
labels: []
scheduled: ""
edges:
  - to: P-7
    ref_version: "0.4.0"
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

<details><summary>⬡ FND-20 · v0.1.0</summary>

```yaml
id: FND-20
type: FND
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: P-1「受付・パース」は構造化ノードセットを生成するが、本文の責務記述にパース段検証（RULE-023〜028）が含まれていない。対応する SPEC-2（RULE-023）・SPEC-32（RULE-024）・SPEC-33（RULE-025）・SPEC-34（RULE-026）・SPEC-35（RULE-027）・SPEC-36（テンプレ由来 RULE-025/026）・SPEC-52（スキーマ適合）・SPEC-53（RULE-028）が、どの P からも参照されない無主状態であり、FR/SPEC の裏付けを持つ機能が分析層のプロセスに接続されていない＝価値経路の穴（PR6）。P-1 はパース処理そのものを担うため、これらパース段検証は P-1 の単一責務（パース段処理）に含めるのが妥当である。
**対応状況**: resolved
**対応内容**: P-1 の責務記述を「パース＋パース段検証（RULE-023〜028）」に明確化し、SPEC-2/32/33/34/35/36/52/53 への依存辺を P-1 に追加した（P-2-2 が複数 RULE を1責務で持つのと同様、パース段処理は単一責務として保持し分解しない）。SPEC-36（テンプレ由来の必須欠如）はその期待動作が RULE-025/026 の検出報告であり、検出主体は P-1（パース段）であるため P-1 に接続（VERIFY-3 後の spec-inspector 点検 G1 を反映）。P-1 に `→FND-20` バックリファレンス辺を付与済み（processes.md v0.6.3→0.6.4）。なお SPEC-31（empty・in-graph 0 件）はパースではなく in-graph 集合決定/オーケストレーションの責務のため P-1 には含めず、別途 P-6/orchestration の論点として残す。
**指摘時 ref_version**: P-1 "0.6"（processes.md v0.6.3 時点）

---

## FND-21: P-6 が config.yaml（I-5）を P-5 を経由せず直接読み込んでいる

<details><summary>⬡ FND-21 · v0.1.0</summary>

```yaml
id: FND-21
type: FND
labels: []
scheduled: ""
edges:
  - to: P-6
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: P-6（in-graph 集合決定）の edges に `to: I-5`（config.yaml）があり、DFD Level 1 でも `FS → I-5 → P-6` と config を直接読み込んでいる。設定の読み込み・検証は P-5（設定ファイル読み込み）の単一責務であり、P-6 が config を二重に読むと (a) 設定の解釈が 2 箇所に分散し、(b) 検証済み設定オブジェクトという単一の真実源を経由しない。P-6 は P-5 が生成する検証済み設定オブジェクト（trace_scope を含む）を受け取るべきで、ファイル（I-5）を直接読むべきでない。
**対応状況**: resolved
**対応内容**: 検証済み設定オブジェクトを内部データ D-3 として起票（io.md・D-2 は FND-8 で退役済みのため D-3 を採番）。P-5 を D-3 の生成元（D-3→P-5）、P-6 を消費先（P-6→D-3）に再配線し、P-6 の `to: I-5` 辺を削除した。P-6 に `→FND-21` バックリファレンス辺を付与。
**指摘時 ref_version**: P-6 "0.6"（processes.md v0.6.5 時点）

---

## FND-22: プロセス間の内部データ（データディクショナリ）が D ノードとして未起票

<details><summary>⬡ FND-22 · v0.1.0</summary>

```yaml
id: FND-22
type: FND
labels: []
scheduled: ""
edges:
  - to: D-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: DFD Level 1/2 に現れるプロセス間の中間データ（設定オブジェクト・構造化ノードセット・パース段違反リスト・RULE 違反リスト・カバレッジ計測結果・ノード草案＝tmp）が、図上のラベルとして存在するだけで分析層の入出力台帳（io.md）に D ノードとして起票されていない。D-1（in-graph ファイル集合）のみが唯一の登録済み内部データで、データディクショナリが不完全。プロセス間データを D 化しないと、価値経路の連続性（PR6）と生成元/消費先の追跡が図でしか担保されず機械検証できない。
**対応状況**: resolved
**対応内容**: プロセス間内部データを D-3（設定オブジェクト）・D-4（構造化ノードセット）・D-5（パース段違反リスト）・D-6（RULE 違反リスト）・D-7（カバレッジ計測結果）・D-8（ノード草案＝tmp）として起票し（D-2 は FND-8 で退役済みのため D-3 から採番）、各 D に D→SPEC・D→P（生成元）辺、各消費プロセスに P→D 辺を付与した（io.md・processes.md）。D-1 に `→FND-22` バックリファレンス辺を付与。
**指摘時 ref_version**: D-1 "0.6"（io.md v0.6.7 時点）

---

## FND-23: P-7-1 に ACTOR-1 からの「ノード記載内容」入力が欠如し O-3 を生成できない

<details><summary>⬡ FND-23 · v0.1.0</summary>

```yaml
id: FND-23
type: FND
labels: []
scheduled: ""
edges:
  - to: P-7-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: P-7-1（著作・tmp 出力）の入力は I-7（テンプレート）のみで、仕様著者（ACTOR-1）が著作したい「ノードの記載内容（型・親 ID・辺・本文）」を受け取る入力が台帳に存在しない。テンプレートだけでは中身が決まらず、O-3（著作済みノードファイル）を生成できない＝価値経路の穴（PR6）。著作の本質的入力である記載内容を I ノードとして明示する必要がある。
**対応状況**: resolved
**対応内容**: ACTOR-1 発の入力 I-9（ノード記載内容）を起票（io.md・I-8 は FND-10 で退役済みのため I-9 を採番）。P-7-1 に消費辺 `to: I-9` を付与し、SPEC-54（FR-13 配下・P-7 が I-7＋I-9 を受け取り O-3 を生成）を新設して I-9 と P-7-1 を SPEC-54 に接続した。P-7-1 に `→FND-23` バックリファレンス辺を付与。
**指摘時 ref_version**: P-7-1 "0.6"（processes.md v0.6.5 時点）

---

## FND-24: H1: SPEC-14-1 RULE-006 違反（FR/NFR への直接辺なし）

<details><summary>⬡ FND-24 · v0.1.0</summary>

```yaml
id: FND-24
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-14-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: SPEC-14-1（カバレッジテーブルの出力フォーマット・normal）の edges が `to: SPEC-14`（親 SPEC）と `to: FND-18` のみであり、FR または NFR への直接辺が存在しない。config.yaml の `must_link_to: SPEC → [FR, NFR]`（RULE-006・severity: error）違反。SPEC-14-1 は SPEC-14 の -N 分割ノードだが、config の必須接続は FR/NFR への直辺を要求しており、SPEC→SPEC のみでは RULE-006 を満たさない。
**推奨**: config の `must_link_to` の OR リストを `SPEC → [FR, NFR, SPEC]` に拡張し、子 SPEC（`-N` 採番）を機構として持つ。あるいは SPEC-14-1 に `to: FR-6` 直辺を付与する。**前者を推奨**（子 SPEC を今後も使うなら機構として持つべきで、SPEC-48 本文・接続マトリクスの意図と一致する）。本 PR が初めて子 SPEC（`-N` 採番）パターンを導入したが、config 側に `SPEC → SPEC` が用意されていなかった点が根因。
**対応状況**: resolved
**対応内容**: `docs/doc-system/config.yaml` の `must_link_to: SPEC` を `target: [FR, NFR, SPEC]` に拡張（FND-25 と同根一括解消）。SPEC-14-1 に `→FND-24` バックリファレンス辺を付与（spec.md v0.3.6）。接続マトリクス §2 SPEC 行に NFR ✅・SPEC ✅ を追加（connection-matrix.md v0.2.1）。
**指摘時 ref_version**: SPEC-14-1 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）

---

## FND-25: M1: SPEC-48 本文が SPEC→SPEC を有効と明記するが config はそれを強制しない矛盾

<details><summary>⬡ FND-25 · v0.1.0</summary>

```yaml
id: FND-25
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-48
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-48（各ノードは直接の親のみへ辺を張る・USDM 1段制約）の本文に「接続マトリクスで SPEC の直接親は FR または別 SPEC と定義されている」「SPEC の `edges[].to` が FR・NFR・または別 SPEC（直接親 SPEC）を指す」と明記されている。一方 config.yaml の `must_link_to: SPEC → [FR, NFR]` には SPEC→SPEC は含まれておらず、機械検査上は SPEC→SPEC のみのノードが RULE-006 ERROR になる。FND-24（SPEC-14-1）の違反はこの不整合が根因。SPEC-48 本文か config の `must_link_to` のいずれかを修正する必要がある。
**推奨**: FND-24 と同根のため一括解消する。config を `SPEC → [FR, NFR, SPEC]` に拡張すれば、SPEC-48 本文（「SPEC の辺は FR・NFR・または別 SPEC を指す」）と config の機械判定が一致する。config を拡張せず SPEC-48 本文側を狭める選択肢もあるが、子 SPEC パターンを採用する方針なら config 拡張を推奨。
**対応状況**: resolved
**対応内容**: FND-24 と同根一括解消。`docs/doc-system/config.yaml` を `SPEC → [FR, NFR, SPEC]` に拡張することで SPEC-48 本文の記述と config の機械判定が一致した。SPEC-48 に `→FND-25` バックリファレンス辺を付与（spec.md v0.3.6）。
**指摘時 ref_version**: SPEC-48 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）

---

## FND-26: H2: docs/doc-system/03-connection-matrix.md が DD-5 と未同期で矛盾

<details><summary>⬡ FND-26 · v0.1.0</summary>

```yaml
id: FND-26
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-5
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: DD-5（NFR から SPEC 導出を必須化・2026-06-13 反映完了）により config.yaml が `must_link_to: SPEC → [FR, NFR]` に更新され `must_be_linked_from: NFR ← [SPEC]` が追加されたが、`docs/doc-system/03-connection-matrix.md`（v0.2.0）は更新されていない。具体的な不整合：§2 接続要否マトリクス表の SPEC 行が FR のみ必須（NFR なし）・§4「NFR は `refines` 上流にはならない（他要素が NFR を refines しない）」が DD-5 の「SPEC→NFR を必須化」と直接矛盾。接続マトリクスは「人が読める全体像」として正本 config.yaml と一致すべきだが、DD-5 適用後に同期されていない。
**推奨**: `docs/doc-system/03-connection-matrix.md` を DD-5 に合わせて §2/§3/§4 とも改訂する。具体的には (§2) must_link_to の mermaid を `SPEC --> FR` のみから `[FR, NFR]` 相当へ拡張・(§3) 被依存表に `NFR ← SPEC` を追加（現状 `NFR ← FND/TC/VERIFY` のみ）・(§4)「NFR は refines 上流にはならない（他要素が NFR を refines しない）」の記述を DD-5（`SPEC → NFR` 必須化）と整合する形に改訂。正本ドキュメント間（config と接続マトリクス）の矛盾を残したまま DD-5 を decided にするのは「矛盾は停止して打ち上げ」原則（PR）違反であり、マージ前解消が望ましい。
**対応状況**: resolved
**対応内容**: `docs/doc-system/03-connection-matrix.md` を v0.2.1 に改訂。§1 mermaid に `SPEC --> NFR` と `SPEC --> SPEC` を追加、§2 表に NFR 列を追加（SPEC 行: FR ✅・NFR ✅・SPEC ✅）、§3 被依存表に `NFR ← SPEC`（requirements 以降）行を追加、§4 テキストを DD-5 に合わせて改訂。DD-5 に `→FND-26` バックリファレンス辺を付与（decisions.md v0.1.6）。
**指摘時 ref_version**: DD-5 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-27: H3: doc-system/03-analysis/00-dfd.md が out-of-graph 自称するが trace_scope.exclude に未登録

<details><summary>⬡ FND-27 · v0.1.0</summary>

```yaml
id: FND-27
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-7
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: `doc-system/03-analysis/00-dfd.md`（v0.2.2）の本文に「本ファイルは派生図（ノードを持たない）」と記載され out-of-graph を自称するが、config.yaml の `trace_scope.include: ["doc-system/**/*.md"]` に含まれ、`trace_scope.exclude` には未登録。spec-inspector はこのファイルを走査しノードを抽出しようとするが、ファイル内には `<details>` YAML ブロックのノードが存在しないため「in-graph ファイルだがノードゼロ」という矛盾状態になる。修正方針：(A) `trace_scope.exclude` に `"**/00-dfd.md"` を追加して out-of-graph を正式化 か (B) out-of-graph 自称を削除しノードを持たない in-graph ファイルとして運用。
**推奨**: **(A) を推奨**。`trace_scope.exclude` に `**/00-dfd.md`（または `doc-system/**/00-dfd.md`）を追加して out-of-graph を正式化する。dashboard を `**/00-dashboard.md` で除外しているのと同じ機構であり、自称と config の食い違い（観測できない前提）を解消できる。
**対応状況**: resolved
**対応内容**: 推奨案 A を採用。`docs/doc-system/config.yaml` の `trace_scope.exclude` に `"**/00-dfd.md"` を追加し、DFD 図ファイルを out-of-graph として正式化した（00-dashboard.md と同等の扱い）。DD-7 に `→FND-27` バックリファレンス辺を付与（decisions.md v0.1.6）。
**指摘時 ref_version**: DD-7 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-28: M2: SPEC-44〜54/SPEC-14-1/FR-15/16 追加バッチを対象とした VERIFY が存在しない

<details><summary>⬡ FND-28 · v0.1.0</summary>

```yaml
id: FND-28
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FR-15
    ref_version: "0.1.0"
  - to: SPEC-54
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: VERIFY-1（2026-06-11）・VERIFY-2（2026-06-12 N0 再点検）・VERIFY-3（2026-06-13 P 単一責務）は、それぞれの対象範囲以降に追加された SPEC-44〜54・SPEC-14-1・FR-15/16 を含まない。これらの追加バッチ（NFR→SPEC 導出強化・依存グラフ機能・SPEC-14-1 など）について spec-inspector による参照整合・カバレッジ・RULE 検査の記録がなく、FND-24（SPEC-14-1 RULE-006 違反）が VERIFY から漏れた事実も VERIFY 空白を示す。追加バッチ全体を対象とした VERIFY を起票する必要がある。
**補足**: dashboard の「ステージ別完成度」は requirements を「✅ N0 再点検済」と表示しているが、06-13 に追加された SPEC-44〜54・SPEC-14-1・FR-15/16 は VERIFY で再走査されておらず、実際 H1（FND-24）のような未検出違反が残っている。「✅点検済」表示が実態を上回っている。
**推奨**: 追加分を対象とした VERIFY を起票する（H1〜H3 解消後にまとめて再走査するのが望ましい）か、requirements 層のステータスを 🟡 に戻す。
**対応状況**: resolved
**対応内容**: H1〜H3 処置（FND-24〜27・2026-06-14）完了後、SPEC-44〜54・SPEC-14-1・FR-15/16 を対象とした VERIFY-5 を起票（01-doc-verify.md v0.1.5）。手動点検で PASS を確認。SPEC-14-1 の RULE-006 違反（FND-24）は H1 処置で解消済みであることを確認した。バックリファレンス辺は VERIFY-5 の edges に `→FND-28` を含む形で付与済み。
**指摘時 ref_version**: FR-15 "0.2"（doc-system/02-what/01-fr.md v0.2.5 時点）、SPEC-54 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）

---

## FND-29: M3: PR #21 説明文が実変更と大きく乖離

<details><summary>⬡ FND-29 · v0.1.0</summary>

```yaml
id: FND-29
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: P-7-2
    ref_version: "0.1.0"
  - to: FND-38
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: PR #21 の説明文は VERIFY-2（N0 再点検）・FND-16/17 副次発見・Q-1 起票のみを記述しているが、実際の PR は16コミット・31ファイル変更を含む大幅な追加があり、説明と実態が乖離している。実際の内容（VERIFY-3・DD-2〜7・SPEC-44〜54・SPEC-14-1・FR-15/16・D-3〜D-8・I-9・P-7→P-7-1/P-7-2・DFD Level 0/1/2・config.yaml 更新・エージェント更新・PEND-2・FND-18〜23 解消）が PR 説明に反映されていない。調停プロセス（P-7-2）が生成した成果物（O-3・著作済みノードファイル群）と PR 説明の間に整合が取れていない状態。
**対応状況**: resolved（PR #21 本文を最新状態に更新済み）
**バックリファレンス辺**: PR #21 description は GitHub 上の out-of-graph 成果物であり in-graph ノードではないため、`→FND-29` バックリファレンス辺の付与先ノードが存在しない。
**指摘時 ref_version**: P-7-2 "0.6"（doc-system/03-analysis/03-processes.md v0.6.6 時点）

---

## FND-30: M4: ダッシュボード「判断待ち 計 0 件」と N1 記載の自己矛盾

<details><summary>⬡ FND-30 · v0.1.0</summary>

```yaml
id: FND-30
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-7
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: doc-system/00-dashboard.md の「オーナー判断待ち（サマリ）」セクションに「計 0 件」と記載されているが、同じダッシュボードの「推奨ネクストアクション」テーブルには N1「current_stage を analysis へ進める判断・🟡 中」が「判断待ち」として掲載されており自己矛盾。N1 はオーナーが判断すべき未決項目であり「計 1 件」が正しい。
**対応状況**: resolved（ダッシュボードの「計 0 件」→「計 1 件」に修正し、N1 を判断待ちテーブルに追加済み）
**バックリファレンス辺**: 00-dashboard.md は `trace_scope.exclude` に登録された out-of-graph ファイル（ノードを持たない）であり in-graph ノードではないため、`→FND-30` バックリファレンス辺の付与先ノードが存在しない。
**指摘時 ref_version**: DD-7 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-31: L1: DD 影響範囲のバージョン注記が現在の frontmatter と乖離

<details><summary>⬡ FND-31 · v0.1.0</summary>

```yaml
id: FND-31
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-5
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: 各 DD の「影響範囲」に記載されたファイルのバージョン注記（例：`doc-system/02-what/03-spec.md`（v0.3.0→0.3.1）等）は、DD 決定時点のバージョン遷移を記録したものだが、その後の追加変更でファイルは更に版上げされており、影響範囲に書かれたバージョンが「当時の変更前後」であって「現在の最終版」を示さないことが不明瞭。読者が DD の影響範囲と現在のファイル版を照合しようとすると乖離が見つかる（例：DD-5 影響範囲では spec.md が v0.3.0→0.3.1 と記載されているが現在は v0.3.5）。DD は決定時点のスナップショットとして書かれているが（DD-2 により suppress[RULE-004] がある）、注記の意図が明示されていないため混乱を招く可能性がある。
**補足**（オーナー指摘の版ずれ実例・いずれも DD-2 の suppress[RULE-004] によるスナップショット設計だが監査時に DD→ファイルで版が合わず混乱を招く）: DD-2 影響範囲「doc-verify →0.1.2」が実 0.1.3（現 0.1.4）／DD-4 影響範囲「findings →0.1.4」が実 0.1.9（現 0.1.11）／DD-5・DD-6 影響範囲「spec 0.3.2」が実 0.3.4（現 0.3.5）。加えて VERIFY-3 が DD-2 の影響範囲に未記載。
**推奨**: DD の影響範囲注記が「決定時点のスナップショット」である旨を各 DD またはガイドに明示するか、監査用に「現在版」を併記する運用を検討。
**対応状況**: resolved
**対応内容**: `doc-system/04-verification/04-decisions.md` のプリアンブルに「影響範囲のバージョン注記は決定時点のスナップショット（DD-2 凍結記録設計）」の明示を追加（v0.1.7）。DD-5 に `→FND-31` バックリファレンス辺を付与。
**指摘時 ref_version**: DD-5 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-32: L2: FR-1 ノードバッジ v0.3 と fr.md ファイル version x.y=0.2 の不一致

<details><summary>⬡ FND-32 · v0.1.0</summary>

```yaml
id: FND-32
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FR-1
    ref_version: "0.3.0"
  - to: FND-36
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: `doc-system/02-what/01-fr.md` 内の FR-1 ノードのバッジが `⬡ FR-1 · v0.3` だが、ファイルの frontmatter は `version: "0.2.5"`（x.y=0.2）。バッジの v0.3 はノード自体の改訂回数カウント、ファイル x.y はファイル全体の MAJOR.MINOR という別体系だが、ノードバッジと ref_version（ファイル x.y 基準）の対応関係が記法ガイドに明示されておらず、読者がバッジの意味を誤解する恐れがある。バッジが「ファイルの x.y」を示すと誤解した場合、ref_version: "0.2.0" との乖離（v0.3 vs 0.2）が誤りに見える。なお ref_version は `"0.2"` で RULE-004 上は正であり、誤読防止のためバッジ採番ルール（ノード改訂回数 vs ファイル x.y）の記法ガイド明記が望ましい。
**対応状況**: resolved
**対応内容**: `docs/doc-system/04-notation.md` の summary バッジ説明箇所に「バッジは著作・最終更新時のファイル x.y スナップショットであり、ノード改訂カウントではない。現在のファイル x.y と一致しなくても RULE 違反にはならない」旨を追記。FR-1 に `→FND-32` バックリファレンス辺を付与（fr.md v0.2.6）。※本 FND-32 の処置（「ファイル x.y スナップショット」定義）は実態と乖離していたことが FND-36 で指摘され、DD-8 により「ノード固有バージョン（MAJOR.MINOR）」定義に是正済み（2026-06-14）。
**指摘時 ref_version**: FR-1 "0.2"（doc-system/02-what/01-fr.md v0.2.5 時点）

---

## FND-33: L3: tmp 草稿に差し戻し済み SPEC-41〜43 と旧 RULE-028 定義が残存

<details><summary>⬡ FND-33 · v0.1.0</summary>

```yaml
id: FND-33
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-18
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: `tmp/doc-system/spec-41-49.md` に FND-18 初回処置で差し戻し済みの SPEC-41（I-1 完全スキーマ）・SPEC-42（O-2 カバレッジ出力）・SPEC-43（I-7 テンプレート構造）の草稿が残存し、最終 spec.md（v0.3.5）の RULE-028 定義とは異なるバージョンの RULE-028 記述が含まれる。`tmp/doc-system/fnd18-redo.md` にも旧 RULE-028 定義が含まれる。tmp は working draft であり主ファイルとは独立するが、同一 SPEC ID の別定義が検索時に混乱を生む恐れがある。また tmp/doc-system/n5-verify-fnd.md にも RULE-028 への参照がある。
**補足**: `tmp/doc-system/spec-41-49.md` の SPEC-41 は RULE-028 を「unknown field → WARNING」と定義しているが、最終 spec.md の RULE-028 は `labels`/`scheduled`/`edges` の欠如・型不正 → ERROR で**別物**であり、将来の誤参照源になる。tmp 草稿9本が最終版と重複してコミットされている。
**推奨**: tmp をコミットしない運用にする（`.gitignore` 追加など）か、撤去分（差し戻し済み SPEC-41/42/43 を含む草稿）を削除する。
**対応状況**: resolved
**対応内容**: 旧 RULE-028 定義を含む草稿 `tmp/doc-system/spec-41-49.md`（差し戻し済み SPEC-41〜43 を含む）と `tmp/doc-system/fnd18-redo.md` を削除。バックリファレンス辺の付与先は tmp ファイル（in-graph ノードなし）のため付与先なし。
**指摘時 ref_version**: FND-18 "0.1"（doc-system/04-verification/02-findings.md v0.1.10 時点）

---

## FND-34: VERIFY-5 点検項目1 の事実誤記（SR-7 → SR-2）

<details><summary>⬡ FND-34 · v0.1.0</summary>

```yaml
id: FND-34
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: VERIFY-5
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: VERIFY-5（doc-system/04-verification/01-doc-verify.md）の点検項目1に「FR-15/16 → SR-7 辺あり ✓」と記載されているが、FR-15・FR-16 の実際の辺はいずれも `to: SR-2`（単一 CLI エントリポイント）であり、SR-7（フェーズ・ステージ進行に応じた検査ノイズ制御）は参照していない。`tmp/doc-system/verify5.md` にも同じ誤記がある。事実誤記であり、PASS 判定（FR→SR 接続あり ✓）自体は正しい（FR-15/16 が SR への接続を持つこと自体は事実のため、結論は不変）。
**推奨**: doc-verify.md と tmp/verify5.md の「SR-7」を「SR-2」に修正し、doc-verify.md を z-bump（v0.1.5→v0.1.6）。再走査不要（結論不変）。
**対応状況**: resolved
**対応内容**: doc-verify.md（v0.1.6）と tmp/verify5.md の点検項目1を SR-2 に修正。VERIFY-5 は suppress[RULE-004] の凍結スナップショットだが、事実誤記の訂正は版内修正として実施。バックリファレンス辺は VERIFY-5 に `→FND-34` を付与（suppress 付き凍結ノードだが訂正記録として）。
**指摘時 ref_version**: VERIFY-5 "0.1"（doc-system/04-verification/01-doc-verify.md v0.1.5 時点）

---

## FND-35: config の `SPEC→[FR, NFR, SPEC]` OR 規則のループホール

<details><summary>⬡ FND-35 · v0.1.0</summary>

```yaml
id: FND-35
type: FND
labels: []
scheduled: "sprint-2"
suppress: []
edges:
  - to: SPEC-48
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: FND-24 処置で config.yaml の `must_link_to: SPEC` を `target: [FR, NFR, SPEC]` に拡張した。この OR 判定では SPEC→SPEC 辺（親 SPEC への辺）だけで RULE-006 を満たせるため、`-N` 採番の子 SPEC を意図した設計だが、任意の SPEC→SPEC 辺（兄弟 SPEC・無関係な SPEC への辺）でも合格してしまい、本来必要な FR/NFR への上流接続を機械検査で強制できない抜け穴がある。現存する全 SPEC に `-N` 子パターン以外の SPEC→SPEC 辺はないため現時点は実害ゼロだが、今後 SPEC が増えると意図しない抜け穴になり得る。
**推奨**（次スプリント対応・本スプリントは起票のみ）: ① config/inspector に SPEC→SPEC の「子孫型」制約（target SPEC の ID が自ノードの `-N` 直接親であること）を追加、② SPEC-48 本文に運用ガイドとして「SPEC→SPEC 辺は `-N` 採番の直接親のみ」を明記、③ spec-inspector 実装時に SPEC→SPEC 辺の有効性を `-N` suffix で追加検証するロジックを組み込む。**推奨は ②＋③**（記法ガイドで運用ルールを明記しつつ、実装時に inspector ロジックで補完。①の config だけでは ID パターン照合が config スキーマを複雑化する）。
**対応状況**: open（**オーナー承認済み sprint-2** — 2026-06-14・独断のスケジュールではなくオーナー判断で sprint-2 に確定）
**指摘時 ref_version**: SPEC-48 "0.1"（ノードバージョン基準・DD-8。当初記録の file x.y="0.3"〔spec.md v0.3.6 時点〕は DD-8 移行で SPEC-48 ノードバッジ x.y="0.1" に再基準化）

---

## FND-36: ノードバッジの意味が実態と矛盾（FND-32 処置の誤定義・オーナー判断論点）

<details><summary>⬡ FND-36 · v0.1.0</summary>

```yaml
id: FND-36
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-32
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: FND-32 処置（前コミット）で `docs/doc-system/04-notation.md` の summary バッジ説明を「著作・最終更新したときのファイル x.y スナップショット」と定義した。しかしこの定義は実態と矛盾する。FR-1 のバッジは `v0.3` だが `01-fr.md` の version 履歴は 0.2.2→0.2.5→0.2.6 で **0.3 に達したことがない**。FR-11 のバッジ `v0.4` も同様にファイル x.y では説明不能。バッジは実際には**ノード固有の改訂回数（ノードを書き直すたびに増える版）**を表しており、「ファイル x.y スナップショット」という FND-32 の定義では全ノードのバッジが説明できない。FND-32 の処置が実態に反する定義で記法ガイドを固定してしまった（前処置の誤り）。元の notation.md 定義「ノードが書かれた時点のファイル x.y」も同様に実態と矛盾していた（FND-32 はこの矛盾の半分しか直していない）。
**推奨**（選択肢・オーナー判断必須）:
- **A. バッジ＝ノード固有のリビジョン番号**と定義し直す（改訂のたびに増える vN.M）。実態に合致し修正は notation.md の説明文のみ（全ノードのバッジは現状維持で有効）。ref_version（ファイル x.y 基準）とは別体系であることを明記。
- **B. バッジ＝ファイル x.y を維持**し、全ノードのバッジ表示を現ファイル x.y に一括修正（FR-1 v0.3→v0.2 等）。大量修正でノード改訂履歴の情報が失われる。
- **C. バッジ廃止**（人の目印に過ぎず ref_version が真実源のため）。
- **推奨 A**（実態に合致・修正最小・ノード単位の改訂履歴として意味がある）。決定はオーナー。
**対応状況**: resolved
**対応内容**: DD-8（「ノードバッジをノード固有バージョン（x.y.z）に正式化・ファイルフロントマター version 廃止」・2026-06-14 オーナー確定）により、バッジをノード固有バージョン（MAJOR.MINOR）として正式化する選択肢 A を採用。`docs/doc-system/04-notation.md` の summary バッジ説明を「ノード固有バージョン（MAJOR.MINOR）、著作・更新のたびに独立して管理される（DD-8）」に改訂し、FND-32 処置の誤定義（「ファイル x.y スナップショット」）を上書き訂正。FND-32 に `→FND-36` バックリファレンス辺を付与。ファイルフロントマター廃止・全辺 ref_version 移行は sprint-2 以降（DD-8 決定）。
**指摘時 ref_version**: FND-32 "0.1"（doc-system/04-verification/02-findings.md v0.1.14 時点）

---

## FND-37: tmp 草稿のコミット運用が継続されていない

<details><summary>⬡ FND-37 · v0.1.0</summary>

```yaml
id: FND-37
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-33
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: FND-33 で「tmp をコミットしない運用（`.gitignore` 追加など）」を推奨し旧草稿を削除したが、本 PR #22 で新たに `tmp/doc-system/verify5.md` がコミットされた（Stop フックの untracked 検知による）。FND-33 推奨の tmp 非コミット運用が継続されていない。なお verify5.md の本文は VERIFY-5 として 01-doc-verify.md に反映済みであり tmp 版は冗長。
**推奨**: `.gitignore` に `tmp/` を追加して tmp を非コミット化するか、tmp を「著作エージェント出力の履歴成果物」として意図的に追跡する運用をオーナーと合意する。現状は方針未確定のまま Stop フックに従って都度コミットされており一貫性がない。
**対応状況**: resolved
**対応内容**: オーナー判断（2026-06-14）で「`.gitignore` に `tmp/` を追加して非コミット化」を採用。`.gitignore` に `tmp/` を追記し、追跡済みの tmp 草稿（tmp/doc-system/・tmp/sprint-1/）を `git rm --cached` でインデックスから除去（ローカルには残置）。草稿は reconciliation が本ファイルへ反映するため履歴成果物ではなく、非コミット化が妥当（FND-33 推奨の継続）。
**指摘時 ref_version**: FND-33 "0.1"（doc-system/04-verification/02-findings.md v0.1.14 時点）

---

## FND-38: PR #22 説明文が実変更と大きく乖離（FND-29 再発）

<details><summary>⬡ FND-38 · v0.1.0</summary>

```yaml
id: FND-38
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-29
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: PR #22 のタイトル「fix: H1/H2/H3 処置（FND-24〜27 resolved）」および本文は、H1/H2/H3 処置のみを記述しており、以下の大規模変更が一切記載されていない：DD-8 確定（ノードバージョニング全面移行）・ファイルフロントマター全廃（30ファイル超）・ref_version 意味論変更（ファイル x.y → ノードバッジ x.y）・live 辺 170 件再基準化・RULE-004/meta-schema/notation/config 再定義・FND-34〜37 起票および一部 resolved・`.gitignore` 追加による tmp 非コミット化（−2400 行超）。PR #21 レビューで起票した FND-29（PR 説明文乖離）の再発であり、レビュアーが実際の変更範囲（プロジェクトのバージョニング哲学の構造的変更）を正しく評価できない状態になっている。
**推奨**: PR 分割はしない（オーナー方針）。PR タイトルと本文を実態に合わせて更新する（タイトル例：`feat: H1/H2/H3 処置 + DD-8 ノードバージョニング全面移行`・本文に全変更の概要を追記）。
**対応状況**: resolved
**対応内容**: PR タイトルを `feat: H1/H2/H3 処置 + DD-8 ノードバージョニング全面移行（FND-24〜37 反映）` に更新し、本文に全変更区分（DD-8 移行・フロントマター全廃・ref_version 再基準化・FND-34〜37・tmp 非コミット化）の概要を追記した。
**指摘時 ref_version**: FND-29 "0.1"（doc-system/04-verification/02-findings.md v0.1.8 時点）

---

## FND-39: DD-8 影響範囲に自己矛盾行残存（「✅ 完了」と「sprint-2 以降」が同居）

<details><summary>⬡ FND-39 · v0.1.0</summary>

```yaml
id: FND-39
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-8
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: `doc-system/04-verification/04-decisions.md` の DD-8「影響範囲」セクションに、フロントマター削除について「doc-system 配下…全ファイルから削除完了。✅ 完了」と宣言している行と、直後に「**ファイルフロントマター `version:` 削除**: sprint-2 以降に順次対応。」という旧版の残骸行が共存しており、直接矛盾している。DD-8 影響範囲を即時実施版に書き換えた際に旧文の一行が残存したもの。
**推奨**: 矛盾行（「sprint-2 以降に順次対応」行）を削除し、DD-8 バッジを z バンプ（内容のみの修正のため ref_version 伝播不要）。末尾の FND-36 関連行は実施済みの記録として保持するが「※以下は当初起票時の実施計画（実施済み）」と一言添えると明確。
**対応状況**: resolved
**対応内容**: 矛盾行（「sprint-2 以降に順次対応」）を decisions.md から削除し、末尾の FND-36 関連行に「※実施済み確認記録」の注記を追加。DD-8 バッジを z バンプ（v0.1 → 表記上は v0.1 のまま、z バンプは省略）。
**指摘時 ref_version**: DD-8 "0.1"（doc-system/04-verification/04-decisions.md 時点）

---

## FND-40: SPEC-1 期待動作が「生成・id一致・エラーなし」の複数アサーション混載でテスタブル基準違反

<details><summary>⬡ FND-40 · v0.1.0</summary>

```yaml
id: FND-40
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-1
    ref_version: "0.3.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-1 の `**期待動作**` が、テスタブル基準「`【条件】のとき、〇〇を▲▲する`（単一条件→単一目的語→単一動詞）」に違反し、「ノード1件を生成する」「PREFIX-N と id が一致する」「エラーを出力しない」の3アサーションを1ノードに混載している。1ノード=1判定にならず、TR の PASS/FAIL がどのアサーションに対するものか曖昧になる。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-1-1/1-2/1-3
**指摘時 ref_version**: SPEC-1 "0.3"（ノードバッジ x.y 基準・DD-8）

---

## FND-41: SPEC-2 期待動作が「ERROR出力・当該中断・後続不発火・他ファイル継続」の4動作混載

<details><summary>⬡ FND-41 · v0.1.0</summary>

```yaml
id: FND-41
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-2
    ref_version: "0.3.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-2 の `**期待動作**` が、「ERROR を出力する」「当該ファイルの処理を中断する」「後続 RULE-024〜027 を発火させない」「他ファイルの処理を継続する」の4動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。fail-close の副作用（中断・継続）も独立アサーションとして許容しない方針（オーナー方針 2026-06-14）に反する。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-2-1/2-2/2-3/2-4
**指摘時 ref_version**: SPEC-2 "0.3"（ノードバッジ x.y 基準・DD-8）

---

## FND-42: SPEC-3-2 期待動作が「IDを永続させる・意味はheadingが担う」の2アサーション混載

<details><summary>⬡ FND-42 · v0.1.0</summary>

```yaml
id: FND-42
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-3-2
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-3-2 の `**期待動作**` が、「ID を永続させる」「意味は heading が担う」の2文・2アサーションを1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。2つの異なる主張が1ノードに同居し検証単位として分離できない。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-3-2-1/3-2-2
**指摘時 ref_version**: SPEC-3-2 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-43: SPEC-3-3 期待動作が「親→子辺は不要・親が存在すれば正常」の2アサーション混載

<details><summary>⬡ FND-43 · v0.1.0</summary>

```yaml
id: FND-43
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-3-3
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-3-3 の `**期待動作**` が、「親→子辺は不要」「親 I-1 が存在すれば正常」の2アサーションを1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。否定アサーション（辺不要）と正常判定アサーション（親存在）が同居し、それぞれ別条件・別目的語のため独立検証できない。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-3-3-1/3-3-2
**指摘時 ref_version**: SPEC-3-3 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-44: SPEC-6 期待動作が「RULE-007 ERROR報告」と「always_errorで抑制不可」の併載

<details><summary>⬡ FND-44 · v0.1.0</summary>

```yaml
id: FND-44
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-6
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-6 の `**期待動作**` が、「RULE-007 で ERROR を報告する」という検証動作アサーションに加えて、「always_error のため抑制不可」という抑制可否の独立文を併載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。検証動作の検証と抑制不可性の検証は別目的語・別条件であり1ノードに混在させるべきでない。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-6-1/6-2
**指摘時 ref_version**: SPEC-6 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-45: SPEC-10 期待動作が「ドリフト検出・再反映を促す」の2動詞混載

<details><summary>⬡ FND-45 · v0.1.0</summary>

```yaml
id: FND-45
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-10
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-10 の `**期待動作**` が、「ドリフトを検出する」「再反映を促す」の2動詞を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。検出（判定）と促し（報告メッセージ）は別動作であり、それぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-10-1/10-2
**指摘時 ref_version**: SPEC-10 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-46: SPEC-12 期待動作が「ERROR報告・DD→X削除・X→DD追加」の3動作混載

<details><summary>⬡ FND-46 · v0.1.0</summary>

```yaml
id: FND-46
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-12
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-12 の `**期待動作**` が、「RULE-001 で ERROR を報告する」「DD→X を削除する」「X→DD を追加する」の3動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。報告（検証ツールの責務）と辺の削除/追加（著者の処置）が混在し、検証対象が曖昧。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ 分割せず単一アサーションへ書き直し（処置手順は前提条件へ退避・SPEC-12 のまま）
**指摘時 ref_version**: SPEC-12 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-47: SPEC-14-1 期待動作が「ヘッダ行出力・各行出力」＋別フィールド展開で複数アサーション

<details><summary>⬡ FND-47 · v0.1.0</summary>

```yaml
id: FND-47
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-14-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-14-1 の `**期待動作**` が、「ヘッダ行を出力する」「各行を出力する」に加えて出力フォーマット/終了コードを別フィールドで展開しており、複数アサーションが1ノードに混在してテスタブル基準（単一条件→単一目的語→単一動詞）に違反する。出力の各構成要素（ヘッダ・明細行・フォーマット・終了コード）はそれぞれ独立検証可能な単位。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-14-1-1/14-1-2/14-1-3/14-1-4
**指摘時 ref_version**: SPEC-14-1 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-48: SPEC-21-1 期待動作が「評価をスキップ・違反を報告しない」の2動詞混載

<details><summary>⬡ FND-48 · v0.1.0</summary>

```yaml
id: FND-48
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-21-1 の `**期待動作**` が、「評価をスキップする」「違反を報告しない」の2動詞を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。スキップ（評価しない）と非報告（出力しない）は別動作で、それぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-21-1-1/21-1-2）
**指摘時 ref_version**: SPEC-21-1 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-49: SPEC-21-2 期待動作が「元の深刻度で評価・違反があれば報告」の2動詞混載

<details><summary>⬡ FND-49 · v0.1.0</summary>

```yaml
id: FND-49
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21-2
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-21-2 の `**期待動作**` が、「元の深刻度で評価する」「違反があれば報告する」の2動詞を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。深刻度に基づく評価と違反報告は別動作であり、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-21-2-1/21-2-2）
**指摘時 ref_version**: SPEC-21-2 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-50: SPEC-21-3 期待動作が「抑制設定を無視・ERROR報告」＋RULE-007/005の2目的語混載

<details><summary>⬡ FND-50 · v0.1.0</summary>

```yaml
id: FND-50
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21-3
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-21-3 の `**期待動作**` が、「抑制設定を無視する」「ERROR を報告する」の2動詞に加え、対象 RULE-007/RULE-005 の2目的語を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。抑制無視と ERROR 報告は別動作、かつ RULE-007 と RULE-005 は別目的語で、それぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-21-3-1/21-3-2）
**指摘時 ref_version**: SPEC-21-3 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-51: SPEC-21-4 期待動作が「設定エラー報告・判定スキップ・全ルール評価」の3動作混載

<details><summary>⬡ FND-51 · v0.1.0</summary>

```yaml
id: FND-51
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-21-4
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-21-4 の `**期待動作**` が、「設定エラーを報告する」「判定をスキップする」「全ルールを評価する」の3動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。設定エラー報告・該当判定のスキップ・他の全ルール評価継続はそれぞれ別動作であり、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-21-4-1/21-4-2/21-4-3）
**指摘時 ref_version**: SPEC-21-4 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-52: SPEC-23-1 期待動作が「抑制を無視・常にERROR報告」の2動詞＋RULE-007/005併記

<details><summary>⬡ FND-52 · v0.1.0</summary>

```yaml
id: FND-52
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-23-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-23-1 の `**期待動作**` が、「抑制を無視する」「常に ERROR を報告する」の2動詞に加え、対象 RULE-007/RULE-005 の併記で複数目的語を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。抑制無視と ERROR 報告は別動作、RULE-007/005 は別目的語で、それぞれ独立検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-23-1-1/23-1-2）
**指摘時 ref_version**: SPEC-23-1 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-53: SPEC-26 期待動作が「テンプレ全項目包含・複製で RULE-025/026/027 不発火」の2アサーション＋多数目的語混載

<details><summary>⬡ FND-53 · v0.1.0</summary>

```yaml
id: FND-53
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-26
    ref_version: "0.3.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-26 の `**期待動作**` が、「テンプレが全項目を含む」「複製で RULE-025/026/027 が不発火」の2アサーションに加え、RULE-025/026/027 という多数目的語を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。テンプレ完備性の検証と複製時の各 RULE 不発火の検証は別目的語・別条件で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-26-1/26-2/26-3/26-4）
**指摘時 ref_version**: SPEC-26 "0.3"（ノードバッジ x.y 基準・DD-8）

---

## FND-54: SPEC-27 期待動作が「type値/id PREFIX/必須辺方向/本文4項目/RULEチェックリスト」の5目的語を1動詞で提供

<details><summary>⬡ FND-54 · v0.1.0</summary>

```yaml
id: FND-54
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-27
    ref_version: "0.3.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-27 の `**期待動作**` が、「type 値」「id PREFIX」「必須辺方向」「本文4項目」「RULE チェックリスト」の5目的語を「提供する」という1動詞で束ねており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。各構成要素の提供有無は独立に検証可能で、1ノードに5目的語を混載すると TR の PASS/FAIL が曖昧になる。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-27-1〜27-5）
**指摘時 ref_version**: SPEC-27 "0.3"（ノードバッジ x.y 基準・DD-8）

---

## FND-55: SPEC-28 期待動作が「realizes辺照合・設計漏れと紐づけ漏れ検出」の2動作・2目的語混載

<details><summary>⬡ FND-55 · v0.1.0</summary>

```yaml
id: FND-55
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-28
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-28 の `**期待動作**` が、「realizes 辺を照合する」「設計漏れと紐づけ漏れを検出する」の2動作・2目的語（設計漏れ／紐づけ漏れ）を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。照合と検出、かつ2種類の漏れはそれぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-28-1/28-2）
**指摘時 ref_version**: SPEC-28 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-56: SPEC-29 期待動作が「0件で通過・価値経路と分析層接続充足と判定」の2動作混載

<details><summary>⬡ FND-56 · v0.1.0</summary>

```yaml
id: FND-56
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-29
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-29 の `**期待動作**` が、「0件で通過する」「価値経路と分析層接続を満たすと判定する」の2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。0件通過（カウント判定）と接続充足判定（構造判定）は別観点で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-29-1/29-2）
**指摘時 ref_version**: SPEC-29 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-57: SPEC-30 期待動作が「未駆動出力/未定義反応イベント/未消費入力」の3目的語を1報告に混載

<details><summary>⬡ FND-57 · v0.1.0</summary>

```yaml
id: FND-57
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-30
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-30 の `**期待動作**` が、「未駆動出力」「未定義反応イベント」「未消費入力」の3目的語を1つの報告動作に混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。3種類の接続漏れはそれぞれ独立した条件・目的語であり、別々の検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-30-1/30-2/30-3）
**指摘時 ref_version**: SPEC-30 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-58: SPEC-31 期待動作が「違反0/ノード0報告・exit 0・RULE全スキップ」の3動作混載

<details><summary>⬡ FND-58 · v0.1.0</summary>

```yaml
id: FND-58
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-31
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-31 の `**期待動作**` が、「違反0/ノード0を報告する」「終了コード0で終了する」「RULE-005〜027を全スキップする」の3動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。報告・終了コード・ルールスキップはそれぞれ別動作で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-31-1/31-2/31-3）
**指摘時 ref_version**: SPEC-31 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-59: SPEC-32 期待動作が「ERROR出力・ファイル中断」の2動作混載

<details><summary>⬡ FND-59 · v0.1.0</summary>

```yaml
id: FND-59
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-32
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-32 の `**期待動作**` が、「ERROR を出力する」「ファイルを中断する」の2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。fail-close の副作用（中断）も独立アサーションとして許容しない方針（オーナー方針 2026-06-14）に反し、出力と中断は別々の検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-32-1/32-2）
**指摘時 ref_version**: SPEC-32 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-60: SPEC-33 期待動作が「ERROR出力・後続RULE中断」の2動作混載

<details><summary>⬡ FND-60 · v0.1.0</summary>

```yaml
id: FND-60
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-33
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-33 の `**期待動作**` が、「ERROR を出力する」「後続 RULE を中断する」の2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。fail-close の副作用（後続中断）も独立アサーションとして許容しない方針（オーナー方針 2026-06-14）に反し、出力と中断は別々の検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-33-1/33-2）
**指摘時 ref_version**: SPEC-33 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-61: SPEC-34 期待動作が「ERROR出力・後続RULE中断」の2動作混載

<details><summary>⬡ FND-61 · v0.1.0</summary>

```yaml
id: FND-61
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-34
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-34 の `**期待動作**` が、「ERROR を出力する」「後続 RULE を中断する」の2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。fail-close の副作用（後続中断）も独立アサーションとして許容しない方針（オーナー方針 2026-06-14）に反し、出力と中断は別々の検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-34-1/34-2）
**指摘時 ref_version**: SPEC-34 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-62: SPEC-35 期待動作が「ERROR出力・後続RULE中断」の2動作混載

<details><summary>⬡ FND-62 · v0.1.0</summary>

```yaml
id: FND-62
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-35
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-35 の `**期待動作**` が、「ERROR を出力する」「後続 RULE を中断する」の2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。fail-close の副作用（後続中断）も独立アサーションとして許容しない方針（オーナー方針 2026-06-14）に反し、出力と中断は別々の検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-35-1/35-2）
**指摘時 ref_version**: SPEC-35 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-63: SPEC-36 期待動作が「RULE-025（id欠如）または RULE-026（type欠如）」の選言目的語混載

<details><summary>⬡ FND-63 · v0.1.0</summary>

```yaml
id: FND-63
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-36
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-36 の `**期待動作**` が、「RULE-025（id 欠如）または RULE-026（type 欠如）」という選言（OR）目的語を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。id 欠如時の RULE-025 発火と type 欠如時の RULE-026 発火は別条件・別目的語であり、それぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-36-1/36-2）
**指摘時 ref_version**: SPEC-36 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-64: SPEC-38 期待動作が「ノードをtmp出力・reconciliationが転記」の2主体・2動作混載

<details><summary>⬡ FND-64 · v0.1.0</summary>

```yaml
id: FND-64
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-38
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-38 の `**期待動作**` が、「ノードを tmp へ出力する」「reconciliation が転記する」の2主体・2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。著作エージェントの tmp 出力と reconciliation の転記は別主体・別動作で、それぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-38-1/38-2）
**指摘時 ref_version**: SPEC-38 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-65: SPEC-39 期待動作が「検証エラー報告・転記中断・id field missing出力」の3動作混載

<details><summary>⬡ FND-65 · v0.1.0</summary>

```yaml
id: FND-65
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-39
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-39 の `**期待動作**` が、「検証エラーを報告する」「転記を中断する」「id field missing を出力する」の3動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。エラー報告・転記中断（fail-close 副作用）・具体メッセージ出力はそれぞれ別動作で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-39-1/39-2/39-3）
**指摘時 ref_version**: SPEC-39 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-66: SPEC-40 期待動作が「一覧を表形式で出力・{形式}で表示」の2文混載

<details><summary>⬡ FND-66 · v0.1.0</summary>

```yaml
id: FND-66
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-40
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-40 の `**期待動作**` が、「一覧を表形式で出力する」「{形式}で表示する」の2文を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。一覧の出力と特定形式での表示は別アサーションで、それぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-40-1/40-2）
**指摘時 ref_version**: SPEC-40 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-67: SPEC-44 期待動作が「読込完了・BOMはWARNING・デコードエラーはERROR」の3分岐混載

<details><summary>⬡ FND-67 · v0.1.0</summary>

```yaml
id: FND-67
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-44
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-44 の `**期待動作**` が、「読込が完了する」「BOM は WARNING」「デコードエラーは ERROR」の3分岐（正常／BOM／デコード失敗）を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。3つの入力クラス（正常・BOM 付き・不正エンコード）はそれぞれ別条件で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-44-1/44-2/44-3）
**指摘時 ref_version**: SPEC-44 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-68: SPEC-45 期待動作が「全importが標準ライブラリのみ・外部依存0件」＋違反出力で複数アサーション混載

<details><summary>⬡ FND-68 · v0.1.0</summary>

```yaml
id: FND-68
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-45
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-45 の `**期待動作**` が、「全 import が標準ライブラリのみを参照する」「外部依存0件である」に加え違反時の出力を含め、複数アサーションを1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。標準ライブラリ参照判定・依存0件判定・違反出力はそれぞれ別観点で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-45-1/45-2）
**指摘時 ref_version**: SPEC-45 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-69: SPEC-46 期待動作が「外部参照パターン非存在・0件確認・検証通過」の複数動作混載

<details><summary>⬡ FND-69 · v0.1.0</summary>

```yaml
id: FND-69
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-46
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-46 の `**期待動作**` が、「外部参照パターンが非存在である」「0件を確認する」「検証を通過する」の複数動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。パターン非存在判定・件数確認・通過判定はそれぞれ別動作で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-46-1/46-2）
**指摘時 ref_version**: SPEC-46 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-70: SPEC-47 期待動作が「version存在・形式適合」と「欠如/空/nullはERROR」の正負2分岐混載

<details><summary>⬡ FND-70 · v0.1.0</summary>

```yaml
id: FND-70
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-47
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-47 の `**期待動作**` が、「version が存在し形式に適合する」（正常）と「欠如/空/null は ERROR」（異常）の正負2分岐を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。存在・形式適合の正常判定と欠如/空/null の異常検出は別条件で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-47-1/47-2）
**指摘時 ref_version**: SPEC-47 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-71: SPEC-48 期待動作が「全辺がFR/NFR/SPECを指す・祖先辺0件・検出時ERROR」の複数アサーション混載

<details><summary>⬡ FND-71 · v0.1.0</summary>

```yaml
id: FND-71
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-48
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-48 の `**期待動作**` が、「全辺が FR/NFR/SPEC を指す」「祖先辺0件である」「検出時 ERROR」の複数アサーションを1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。辺の指す先の妥当性判定・祖先辺の件数判定・違反検出時の ERROR 報告はそれぞれ別観点で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-48-1/48-2）
**指摘時 ref_version**: SPEC-48 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-72: SPEC-49 期待動作が「status系キー非存在・存在でWARNING・状態は本文バッジ」の複数アサーション混載

<details><summary>⬡ FND-72 · v0.1.0</summary>

```yaml
id: FND-72
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-49
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-49 の `**期待動作**` が、「status 系キーが非存在である」「存在で WARNING」「状態は本文バッジが担う」の複数アサーションを1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。キー非存在の正常判定・存在時の WARNING 検出・状態の担い手（本文バッジ）の説明はそれぞれ別観点で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-49-1/49-2）
**指摘時 ref_version**: SPEC-49 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-73: SPEC-50 期待動作が「指定フォーマットでファイル出力・stdoutエラーなし・exit 0」の3動作混載

<details><summary>⬡ FND-73 · v0.1.0</summary>

```yaml
id: FND-73
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-50
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-50 の `**期待動作**` が、「指定フォーマットでファイル出力する」「stdout にエラーがない」「exit 0」の3動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。ファイル出力・stdout 状態・終了コードはそれぞれ別観点で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-50-1/50-2/50-3）
**指摘時 ref_version**: SPEC-50 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-74: SPEC-51 期待動作が「メトリクスレポートstdout出力・exit 0」の2動作混載

<details><summary>⬡ FND-74 · v0.1.0</summary>

```yaml
id: FND-74
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-51
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-51 の `**期待動作**` が、「メトリクスレポートを stdout へ出力する」「exit 0」の2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。レポート出力と終了コードは別観点で、それぞれ独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-51-1/51-2）
**指摘時 ref_version**: SPEC-51 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-75: SPEC-52 期待動作が「RULE-025/026/027/028非発火・終了コード0」の2アサーション混載

<details><summary>⬡ FND-75 · v0.1.0</summary>

```yaml
id: FND-75
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-52
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-52 の `**期待動作**` が、「RULE-025/026/027/028 が非発火である」「終了コード0」の2アサーション（かつ RULE-025〜028 の複数目的語）を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。各 RULE の非発火判定と終了コードはそれぞれ別観点で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-52-1〜52-5）
**指摘時 ref_version**: SPEC-52 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-76: SPEC-53 期待動作が「RULE-028 ERROR 1件出力・後続RULE中断」の2動作混載

<details><summary>⬡ FND-76 · v0.1.0</summary>

```yaml
id: FND-76
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-53
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-53 の `**期待動作**` が、「RULE-028 で ERROR を1件出力する」「後続 RULE を中断する」の2動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。fail-close の副作用（後続中断）も独立アサーションとして許容しない方針（オーナー方針 2026-06-14）に反し、出力と中断は別々の検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-53-1/53-2/53-3）
**指摘時 ref_version**: SPEC-53 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-77: SPEC-54 期待動作が「I-7/I-9充填し草案生成・I-9なしでO-3生成不可・テンプレのみ生成不可保証」の複数アサーション混載

<details><summary>⬡ FND-77 · v0.1.0</summary>

```yaml
id: FND-77
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-54
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-54 の `**期待動作**` が、「I-7 と I-9 を受け取り充填し草案を生成する」「I-9 なしでは O-3 を生成不可」「テンプレのみでは生成不可を保証する」の複数アサーションを1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。正常系の草案生成・I-9 欠如時の生成不可・テンプレ単独時の生成不可保証はそれぞれ別条件で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-54-1/54-2/54-3）
**指摘時 ref_version**: SPEC-54 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-78: SPEC-50/51 の post-mvp と scheduled 表現が不統一（オーナー決定Bで config 改訂方針）

<details><summary>⬡ FND-78 · v0.1.0</summary>

```yaml
id: FND-78
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-50
    ref_version: "0.1.0"
  - to: SPEC-51
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-50/51 は `labels:[post-mvp]` だが `scheduled:""`（空）である。一方 SPEC-28/40 は `scheduled:"post-mvp"` と表現しており、post-mvp の表現が不統一。scheduled は SPEC-20（後フェーズ完全サイレント判定）に影響する属性のため放置不可で、同じ post-mvp 扱いの SPEC 群でラベルと scheduled の使い分けが揺れている。
**推奨**: オーナー決定B（2026-06-14）＝`config.yaml` の `phases` から `post-mvp` を除去し、`scheduled` は実スプリント（sprint-*）のみ許可する。SPEC-28/40/50/51 の `scheduled` を実スプリント（例 sprint-2）へ設定し、`scheduled ∈ phases` を強制する RULE を新設して空 scheduled と非 phases 値を違反化する。config・RULE 一覧・接続マトリクスの改訂を伴うため DD 昇格が望ましい。
**対応状況**: resolved（DD-9 / 2026-06-14）
**指摘時 ref_version**: SPEC-50 "0.1"／SPEC-51 "0.1"（いずれもノードバッジ x.y 基準・DD-8）

---

## FND-79: RULE-006/025/026 が複数 SPEC に分散し全体把握の負荷

<details><summary>⬡ FND-79 · v0.1.0</summary>

```yaml
id: FND-79
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-8
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO
**内容**: RULE-025 を SPEC-33/36/39、RULE-026 を SPEC-34/36、RULE-006 を SPEC-8/15-1/18-1〜5/30 が扱っている。発生源（パース時／テンプレ由来／reconciliation 検証）・一般則／特殊ケースで分離されており矛盾はないが、同一 RULE が多数ノードに散在し全体把握の負荷になる。SPEC-30 は本文で「SPEC-8 の一般則の特殊ケース」と明示している。
**推奨**: 発生源分割の意図を接続マトリクスまたは authoring-guide に索引化し、同一 RULE を扱う SPEC 群を相互参照できるようにする（仕様変更は不要・ドキュメント整備のみ）。
**対応状況**: open
**指摘時 ref_version**: SPEC-8 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-80: PEND 義務辺残存（RULE-022）に対応する failure SPEC が不在

<details><summary>⬡ FND-80 · v0.1.0</summary>

```yaml
id: FND-80
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FR-5
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: FR-5 配下に DD 義務辺残存＝SPEC-12（RULE-001）・Q 義務辺残存＝SPEC-13（RULE-002）はあるが、PEND 義務辺残存（RULE-022 WARNING）を検証する failure SPEC が存在しない。decision_spine の3型（DD/Q/PEND）のうち PEND だけカバレッジが欠落しており、PEND の義務辺残存が検証鎖から漏れている。
**推奨**: FR-5 配下に PEND 義務辺残存（RULE-022）の failure SPEC を新設（SPEC-12/13 と同型）。要否はオーナー確認。
**対応状況**: resolved（2026-06-15）
**処置**: FR-5 配下に SPEC-55「PEND の義務辺残存（failure）」（RULE-022 WARNING・SPEC-12/13 同型）を新設し、decision_spine 3型（DD/Q/PEND）の義務辺残存カバレッジの対称を回復。spec-author が SPEC-55 に `→FND-80` バックリファレンス辺を付与済み。
**指摘時 ref_version**: FR-5 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-81: SPEC-31 の親が FR-1 だが trace_scope 主題の FR-9 が自然

<details><summary>⬡ FND-81 · v0.1.0</summary>

```yaml
id: FND-81
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-31
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: SPEC-31（trace_scope 結果 in-graph 0件・empty）の親辺が `to: FR-1`（ノードグラフ構造化）になっている。しかし in-graph 集合の決定は FR-9（トレース対象集合の宣言・trace_scope）の主題であり、親は FR-9 が自然との議論余地がある。現状 SPEC-24-1/24-2 が FR-9 配下に置かれている。
**推奨**: SPEC-31 の親を FR-9 へ付け替えるか、FR-1 配下に留める根拠（パース正常系の境界＝empty）を本文に明記する。オーナー判断。
**対応状況**: open
**指摘時 ref_version**: SPEC-31 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-82: SPEC-9-1 と SPEC-10 が同一 RULE-004 検出でほぼ同主張

<details><summary>⬡ FND-82 · v0.1.0</summary>

```yaml
id: FND-82
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-10
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO
**内容**: SPEC-9-1（依存辺ドリフト・failure）と SPEC-10（ファイル/ノード x.y 上昇・normal）が、いずれも「依存辺 ref_version の x.y 不一致→RULE-004 ERROR」を主張しほぼ同内容になっている。condition で正/負対の意図と思われるが、視点（辺側の定義 vs 版上昇トリガ）の差が本文で明確でなく重複が近接している。
**推奨**: 両 SPEC の責務境界（9-1=ドリフト定義の failure、10=版上昇トリガの normal）を本文で明示するか、統合を検討する。オーナー判断。
**対応状況**: open
**指摘時 ref_version**: SPEC-10 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-83: always_error 系 SPEC の condition が不揃い（SPEC-6=error, SPEC-7=failure）

<details><summary>⬡ FND-83 · v0.1.0</summary>

```yaml
id: FND-83
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-7
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO
**内容**: RULE-007（存在しない ID 参照）と RULE-005（孤立）はともに always_error だが、対応 SPEC の condition が SPEC-6=error・SPEC-7=failure と不揃いになっている。同じ always_error 性質のルールで condition 軸の付与基準が一貫していない。
**推奨**: always_error 系 SPEC の condition 付与基準（error か failure か）を統一定義し、SPEC-6/7 を整合させる。オーナー判断。
**対応状況**: open
**指摘時 ref_version**: SPEC-7 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-84: SPEC-47/SPEC-44 が DD-8（ファイル frontmatter 全廃）と矛盾

<details><summary>⬡ FND-84 · v0.1.0</summary>

```yaml
id: FND-84
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-47
    ref_version: "0.1.0"
  - to: DD-8
    ref_version: "0.1.0"
```
</details>

**深刻度**: ERROR
**内容**: DD-8（2026-06-14 確定・反映済）でファイル frontmatter `version:` は全廃され、版管理はノードバッジ x.y に移行済みである（config.yaml 冒頭・FND-39・ダッシュボードで確認）。しかし SPEC-47 は「全 in-graph ファイルの frontmatter に `version` フィールドが存在する」ことを ERROR 要求し、SPEC-44（NFR-1）も「YAML フロントマター」を前提にしている。廃止済みの frontmatter を必須化する仕様が残存しており、DD-8 と直接矛盾する。さらに「観測できないものを持たない」原則（PR4）にも反し、検証ツールが存在しない frontmatter version を ERROR 報告してしまう。
**推奨**: SPEC-47 を「全 in-graph ノードの summary バッジに version（x.y）が存在する」検証へ置換、または廃止する。SPEC-44 の本文から frontmatter 前提を除去し、プレーンテキスト/UTF-8 検証に限定する。NFR-1 本文（フロントマター言及）の見直しも要。DD 昇格が望ましい。
**対応状況**: resolved（DD-10 / 2026-06-14）
**指摘時 ref_version**: SPEC-47 "0.1"／DD-8 "0.1"（いずれもノードバッジ x.y 基準・DD-8）

---

## FND-85: SPEC-49-1/49-2 が廃止済み frontmatter を検査対象にしている（DD-8 矛盾）

<details><summary>⬡ FND-85 · v0.1.0</summary>

```yaml
id: FND-85
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-49
    ref_version: "0.1.0"
  - to: DD-8
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: アンブレラ SPEC-49 の概要は「状態は本文見出しバッジにのみ記載される」と正しく述べているが、子 SPEC-49-1/49-2 の前提条件・入力/トリガ・期待動作は「frontmatter に `status:`/`lifecycle:`/`state:` キーが存在するか」を検査対象としている。DD-8（2026-06-14 確定・反映済）でファイルレベル YAML フロントマターは全廃され、ノードデータはインライン YAML ブロック（`<details>` 内）にのみ存在する。したがって「frontmatter」は実在しない検査対象であり、DD-8 および NFR-1（プレーンテキスト・フロントマター廃止）と齟齬する。検査対象が存在しないため、本来検出すべき「ノード YAML ブロックへの status 系キー混入」を取りこぼす恐れがある（PR4: 観測できないものを持たない、にも抵触）。
**推奨**: SPEC-49-1/49-2 本文の「frontmatter」を「ノード YAML ブロック内のフィールド（`<details>` 内インライン YAML）」へ用語訂正する。SPEC-49 概要の表現と整合させる。DD 昇格が望ましい。
**対応状況**: resolved（2026-06-15）
**処置**: SPEC-49/49-1/49-2 の「frontmatter」表記を「ノード YAML（メタ属性）」へ用語訂正（DD-8 準拠）。NFR-6 は既に「メタ属性」表記のため変更不要。spec-author が SPEC-49 に `→FND-85` バックリファレンス辺を付与済み。
**指摘時 ref_version**: SPEC-49 "0.1"／DD-8 "0.1"（いずれもノードバッジ x.y 基準・DD-8）

---

## FND-86: NFR 由来本文検査の出力ルール ID 規約が未定義（{NFR-id}-check vs RULE-NNN）

<details><summary>⬡ FND-86 · v0.1.0</summary>

```yaml
id: FND-86
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-44
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO
**内容**: 横断: SPEC-44〜49（SPEC-44 を代表アンカーとして指摘）。SPEC-44〜49 の出力例は検証ルール ID として `{NFR-id}-check`（例 `NFR-1-check`・`NFR-4-check`）を使用するが、正準ルール台帳は `RULE-NNN`（`docs/doc-system/05-verification.md`）である。NFR 由来の本文検査が正式に RULE 番号を持つのか、`{NFR-id}-check` が暫定識別子なのか、出力契約上の識別子規約が定義されていない。出力契約（O-1 RULE 違反レポート）における違反 ID の名前空間が二重化しており、消費側（reconciliation・spec-inspector）の解釈がぶれる。
**推奨**: NFR 由来検査の出力ルール ID 規約を確定する（RULE-NNN への正式採番 or `{NFR-id}-check` の正式採用）。確定後は台帳（`05-verification.md`）に記載し、SPEC-44〜49 の出力例を統一する。
**対応状況**: resolved（DD-11 / 2026-06-15）
**処置**: DD-11 で `{NFR-id}-check` を NFR 由来本文検査の正式 rule-id 体系として採用（選択肢 B）。`docs/doc-system/05-verification.md` の RULE 台帳に1家族として登録する（reconciliation 反映後に主文脈で実施）。SPEC-44〜49 の出力例は据置。バックリファレンスは DD-11 が `→FND-86` 辺を保持（FND→DD の通常逆転ではなく、DD が解消起点のため DD 側に辺を持つ）。
**指摘時 ref_version**: SPEC-44 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-87: SPEC-30 に分析層 D の接続漏れ失敗系子が欠落

<details><summary>⬡ FND-87 · v0.1.0</summary>

```yaml
id: FND-87
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-30
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING
**内容**: アンブレラ SPEC-30「分析ノードの接続漏れ検出」の子は SPEC-30-1（未駆動出力 O→P 欠如）/30-2（未定義反応イベント E←P 欠如）/30-3（未消費入力 I←P 欠如）の3種だが、分析層 D（内部データ）の接続漏れ（D→P・D←P 欠如）の失敗系子が欠落している。config の `must_link_to: D→P`・`must_be_linked_from: D←P` は RULE-006 対象であり、D の接続漏れも検出されるべき検査対象である。SPEC-8 一般則でカバーされる前提なら、SPEC-30 概要にその旨の明記がなく、検証カバレッジの穴か単なる暗黙包含かが読み取れない。
**推奨**: SPEC-30 に D 接続漏れの failure 子（SPEC-30-4）を追加するか、D は SPEC-8 一般則でカバーされる旨を SPEC-30 概要に明記する。要否（専用子の新設 vs 一般則委譲の明記）はオーナー判断。
**対応状況**: resolved（2026-06-15）
**処置**: 実カバレッジ穴ではない。SPEC-8 一般則（RULE-006）が D→P・P→D をカバーするため専用子は不要。SPEC-30 概要に「D は SPEC-8 でカバー・本傘はアクタ面 O/E/I のみ列挙」と設計意図を明記。spec-author が SPEC-30 に `→FND-87` バックリファレンス辺を付与済み。
**指摘時 ref_version**: SPEC-30 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-88: SPEC-13 の期待動作が条件節文頭のテスタブル様式に整っていない

<details><summary>⬡ FND-88 · v0.1.0</summary>

```yaml
id: FND-88
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-13
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO
**内容**: SPEC-13 の期待動作は「RULE-002 WARNING を報告する（未決論点の影響候補・ERROR には昇格しない）」であり、単一動詞（報告する）・単一目的語（RULE-002 WARNING）は満たすが、条件節が期待動作の文頭に置かれていない（条件「Q の義務辺が存在する」は入力/トリガ欄にのみ記載）。`【条件】のとき、〇〇を▲▲する` の条件節文頭形式で統一する他 SPEC と様式が不統一であり、テスタブル様式の機械抽出（条件→期待のペア化）にブレを生む。なお内容自体は正しく、失敗系の WARNING 報告として妥当。
**推奨**: 期待動作を「Q の義務辺（Q→X）が存在するとき、RULE-002 WARNING を報告する」のように条件節を文頭に置く様式へ整形し、テスタブル様式を全 SPEC で統一する。様式統一は notation/規約での明文化が望ましい。
**対応状況**: open
**指摘時 ref_version**: SPEC-13 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-89: 傘 SPEC の condition が子の condition 多様性を代表せずミスリード

<details><summary>⬡ FND-89 · v0.1.0</summary>

```yaml
id: FND-89
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-44
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO
**内容**: アンブレラ SPEC-44 の `condition: normal` だが、子 SPEC-44-1 は `condition: normal`、SPEC-44-2 は `condition: boundary`（BOM 検出）、SPEC-44-3 は `condition: error`（デコードエラー）と多様である。傘の condition が normal 固定で子の condition 多様性を代表しておらず、形式上ミスリードを招く（傘は非テスタブルのため実害は低い）。同種の傘（複数 condition の子を束ねるアンブレラ）が他にも存在する（横断的論点）。一方、傘から condition を外すと RULE-016（SPEC は condition 必須）に抵触する。
**推奨**: 傘ノードの condition の意味づけ（代表 condition なのか、無効化マーカーなのか）を notation/規約で定義する。RULE-016 との両立のため、condition フィールドを残しつつ傘では `condition: normal`（または `mixed` 等の専用値）の意味を規約側で定義する解を検討する。
**対応状況**: open
**指摘時 ref_version**: SPEC-44 "0.2"（ノードバッジ x.y 基準・DD-8）

---

## FND-90: 検証手順の観測/実行主体が二者択一で一意でない（再現性・観測可能性）

<details><summary>⬡ FND-90 · v0.1.0</summary>

```yaml
id: FND-90
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-45
    ref_version: "0.2.0"
  - to: SPEC-46
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO
**内容**: SPEC-45-1/45-2 の入力/トリガが「reconciliation または CI が」、関連する SPEC-46-1/46-2 が「reconciliation または asset-auditor が」と、観測/実行主体を二者択一で記載している。検証手順の主体が一意でないと、どの主体が実行したかで結果が再現しない懸念があり、観測可能性（PR4）・再現性が揺れる。誰が実行しても同一判定になる機構として明文化されていれば問題ないが、現状の「A または B が」表現はそれを保証していない。
**推奨**: 検証主体を一意化する（単一主体に固定）か、「reconciliation・CI・asset-auditor のいずれが実行しても同一の機械判定を行う」ことを機構として明文化する。SPEC-46（横断的に同種記載あり）も併せて見直す。
**対応状況**: resolved（2026-06-15）
**処置**: 観測主体を一意化（PR4）。SPEC-45-1/45-2 を「CI が」、SPEC-46-1/46-2 を「asset-auditor が」に変更し、「reconciliation または」の二択を解消。横断対象 SPEC-46 もこの finding でカバーするため `→SPEC-46` 辺を追加（指摘時 ref_version: SPEC-46 "0.1"）。spec-author が SPEC-45・SPEC-46 の両傘に `→FND-90` バックリファレンス辺を付与済み。
**指摘時 ref_version**: SPEC-45 "0.1"／SPEC-46 "0.1"（いずれもノードバッジ x.y 基準・DD-8）

---

## FND-91: SPEC-3-1 が人手の ID 採番行為を期待動作とし機械観測が難しい＋例の欠落

<details><summary>⬡ FND-91 · v0.1.0</summary>

```yaml
id: FND-91
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-3-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: SPEC-3-1 の入力/トリガが「著者が新規ノードに ID を付与する」、期待動作が「`PREFIX-N[-N...]` 形式で既存 ID と重複しない一意な ID を採番する」であり、主体が人手（著者）の採番行為になっている。検証ツール（spec-inspector）が観測できるのは「採番された結果の ID が形式に合致し一意か」であって採番行為そのものではない（PR4: 観測できないものを持たない）。期待動作が行為主体視点で書かれており、機械検証可能な「結果状態」への言い換えが望ましい。加えて他 SPEC が持つ `例` 欄が SPEC-3-1 には欠落しており、テスタブル様式の具体例提示が不足している。
**推奨**: 期待動作を「全ノードの ID が `PREFIX-N[-N...]` 形式に合致し、グラフ内で一意である」のような機械検証可能な結果観点へ言い換える。併せて `例`（合致・重複の具体例）を追加する。
**対応状況**: open
**指摘時 ref_version**: SPEC-3-1 "0.1"（ノードバッジ x.y 基準・DD-8）

---

## FND-92: E-1（点検要求）本文が P-8/P-9・O-4/O-5 を反映していない不整合

<details><summary>⬡ FND-92 · v0.1.0</summary>

```yaml
id: FND-92
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: E-1
    ref_version: "0.5.0"
  - to: P-8
    ref_version: "0.1.0"
  - to: P-9
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO
**内容**: DD-6（依存グラフ機能）の分析層補完（N8）で、SPEC-50（`--export-graph`）の処理 P-8（依存グラフ出力処理）・出力 O-4（依存グラフ出力ファイル）、SPEC-51（`--complexity`）の処理 P-9（参照関係複雑度計算処理）・出力 O-5（参照関係複雑度メトリクスレポート）を著作し、トリガを E-1（点検要求）に配線した。一方 E-1（v0.5）本文は更新されておらず、アクション欄が「P-5・P-6 を先行実行し P-1→P-2・P-3→P-4 を順次実行する」のみ、レスポンス欄が「O-1（RULE違反レポート）・O-2（カバレッジ点検結果）」のみで、新設の P-8/P-9・O-4/O-5 を反映していない。`--export-graph`/`--complexity` は同一 spec-inspector 起動のフラグ選択モードであり E-1 配下に置くのが妥当だが、E-1 本文がそのフラグ追加実行と追加出力を記載しておらず、グラフ（P-8/P-9→E-1 辺・O-4/O-5）と E-1 本文の散文記述が乖離している。

**先例**: `--coverage`（P-3-2）も同一 spec-inspector 起動のフラグ選択モードで E-1 トリガであり、E-1 配下に複数フラグの追加実行を置く構成は既存設計と整合する。したがって `--export-graph`/`--complexity` を E-1 配下に置き P-8/P-9 を追加実行・O-4/O-5 を追加出力とするのは既存設計どおりであり、別事象（新 E）の新設は不要。これは「ものと発生源で分ける」原則（PR1）にも合致する（発生源・もの＝同一 spec-inspector 起動・I-1 ノードファイル群で同一、フラグ違いは使い道の差にすぎず事象を割らない）。

**推奨**: E-1 本文を改訂する。
- アクション欄に「`--export-graph` 指定時は P-8（依存グラフ出力処理）、`--complexity` 指定時は P-9（参照関係複雑度計算処理）を追加実行する（`--coverage`／P-3-2 と同じくフラグ選択モード）」を追記。
- レスポンス欄に O-4（依存グラフ出力ファイル）・O-5（参照関係複雑度メトリクスレポート）を追記。
- P-3-2／`--coverage` 先例と整合する純粋な本文反映であり、新規のオーナー判断を要さないため**即時 resolved 可**。

**対応状況**: resolved（2026-06-15）
**処置**: reconciliation が E-1 本文のアクション欄に `--export-graph`→P-8／`--complexity`→P-9 の追加実行（`--coverage`／P-3-2 先例と整合）を、レスポンス欄に O-4・O-5 を追記して改訂し、E-1 に `→FND-92` バックリファレンス辺を付与して処置完了。本文修正・バックリファレンス辺追加はいずれも DD-8 §4 の z バンプに該当するため、E-1 の可視バッジは v0.5 据置・依存元の ref_version 伝播なし（当初 0.5→0.6 へバンプし 11 ライブ P ノードへ伝播させたが、DD-8 §4 に基づき z バンプへ訂正・伝播を巻き戻し）。新事象（新 E）は P-3-2／`--coverage` 先例との整合により不要と判断し著作していない。
**指摘時 ref_version**: E-1 "0.5"（events.md v0.5 時点）／P-8 "0.1"（events.md・N8 著作時点）／P-9 "0.1"（events.md・N8 著作時点）

---

## FND-93: D-4（構造化ノードセット）定義が condition/result/log_ref を欠き P-2-3/P-2-4/P-3-2 の入力が台帳上断絶

<details><summary>⬡ FND-93 · v0.1.0</summary>

```yaml
id: FND-93
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: D-4
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING
**内容**: D-4（構造化ノードセット）の現定義は `id` / `type` / `labels` / `scheduled` / `edges` のみで、**型別拡張フィールド `condition` / `result` / `log_ref` を内部表現に含んでいない**。一方で消費プロセスは次のとおりこれらを必要としていた。
- **P-2-3（カバレッジ属性検査）**: SPEC/TD の `condition` 属性を判定対象とする（RULE-016/017/018/019）。
- **P-2-4（検証層完結性検査）**: TR の `result`・`log_ref` 属性を判定対象とする（RULE-020/021）。
- **P-3-2（仕様カバレッジ計測）**: FR×condition 集計に SPEC/TD の `condition` 属性を必要とする（SPEC-14-1-2）。

これらのプロセスが必要とする属性が D-4 の定義に存在しないため、台帳上はパース段（P-1）から検査段（P-2-3/P-2-4/P-3-2）への入力が**途切れていた**。価値経路は全入力がプロセスを通って出力まで連続して届くことを要求する（PR6）が、condition/result/log_ref を要する検査経路がその起点（D-4）で供給を欠き、価値経路が断絶していた。実装では「ノードファイルに書かれている condition/result/log_ref を P-1 が当然パースしている」前提で暗黙に流れる想定だったが、分析層台帳の D-4 定義がそれを表現しておらず、機械検証・追跡が図でも台帳でも担保されない既存欠陥である。

**対応状況**: resolved
**対応内容**: 本改訂（分析層全面見直し）で次の 2 点により断絶を解消した。
- **D-4 内部表現に明記**: D-4 を「P-1 内部の正規化集合（中間生成物）」として保持しつつ、本文に **condition/result/log_ref を内部表現に含む**ことを明記する（設計 §3 D-4 改訂・§4 改訂ノード一覧）。
- **射影スライスが供給**: P-1-6（検査ビュー射影）が D-4 を消費スライスへ射影し、**D-18（属性検査ビュー＝id・type・condition・result・log_ref・suppress・scheduled・辺）が P-2-3/P-2-4 へ**、**D-21（仕様カバレッジビュー＝FR・SPEC・TD と condition 属性・refines 辺）が P-3-2 へ**当該フィールドを供給する。これにより condition/result/log_ref を要する検査経路の起点供給が成立し断絶が解消する。

reconciliation が D-4（condition/result/log_ref を内部表現に含む旨を本文へ追記・MINOR バンプ。分析層 Pass で実施済み＝D-4 現バッジ v0.2）・D-18・D-21（当該フィールドを含むスライスとして著作）に反映し、**D-4 に `→FND-93` バックリファレンス辺を付与**する（処置対象は D-4＝指摘対象本体であり実在するため付与先あり。本バックリファレンス付与は分析層 io.md Pass で実施）。
**指摘時 ref_version**: D-4 "0.1"（io.md・D-4 ノードバッジ v0.1 時点）

---

## FND-94: 分析層全面見直し起因の被覆ドリフト 2 件（G1 孤児 SPEC・G4 旧 P-3 消費先記述残存）

<details><summary>⬡ FND-94 · v0.1.0</summary>

```yaml
id: FND-94
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: P-2-2-3
    ref_version: "0.2.0"
  - to: D-9
    ref_version: "0.2.0"
  - to: D-14
    ref_version: "0.2.0"
  - to: SPEC-15-1
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING

**内容**: 分析層全面見直し（DD-12）の総点検（spec-inspector）で、被覆マップに見直し起因のドリフトが 2 件残存していることを検出した。

---

**G1（孤児 SPEC・WARNING）**: SPEC-15-1（`SPEC に TD からの被依存辺欠如`・`must_be_linked_from: SPEC ← [TD]`・RULE-006 WARNING を報告する failure 系仕様）が、分析層分解後どの P ノードからも `→SPEC-15-1` で参照されておらず、被覆マップ上の孤児になっている。RULE-006（必須辺欠如）の検出責務は分解後 **P-2-2-3（必須辺欠如検出）** が担う。P-2-2-3 は接続検査ビュー D-17 と必須接続規則 **D-10（`must_link_to`/`must_be_linked_from` の 2 フィールド束）** を照合して RULE-006 必須辺欠如違反候補を出力するプロセスであり、`must_be_linked_from: SPEC ← [TD]`（config.yaml 行 81）は D-10 に含まれる規則である。したがって SPEC-15-1（RULE-006 による SPEC←TD 被依存辺欠如検出）の被覆主体は P-2-2-3 が正しい。

- **処置**: P-2-2-3 に `→SPEC-15-1`（ref_version "0.1"）を付与し、被覆を成立させた（P-2-2-3 MINOR バンプ v0.1→v0.2）。
- **確認結果**: D-10 が `must_be_linked_from`（SPEC ← [TD] を含む）と `must_link_to` の両方を束ねていることを io.md の D-10 定義本文（「含むフィールド: must_link_to … must_be_linked_from …」）で確認済み。P-2-2-3 はその D-10 全体を消費して RULE-006 を一手に検査するため、TD→SPEC 系も含めて P-2-2-3 が担当する。よって P-2-4 系（FND-TC-VERIFY 必須辺検査＝検証層 must_link_to の verification 行のみ担当）が SPEC←TD を担う代替は不要。

---

**G4（台帳記述ドリフト・WARNING）**: D-9（フェーズ・ステージ状態）・D-14（ルール発火ステージ表）の「消費先」記述に、旧「**P-3（カバレッジ点検・発火制御）**」が残存していた（io.md）。DD-12(b) で**発火制御は P-2-5（抑制・発火フィルタ）に一元化**されたため、D-9・D-14 を発火制御目的で消費するのは P-2-5 であり、P-3 は発火制御の消費者ではない。実 edges でも齟齬が確認できた。

- **D-9 の実消費（edges 上）**: P-1-4（スキーマ検証・scheduled 値ドメイン照合）・P-2-5（抑制・発火フィルタ）が `→D-9` を持つ。P-3 系に `→D-9` 辺は存在しない。だが D-9 本文の消費先列は「P-1-4・P-2-5・**P-3（カバレッジ点検・発火制御）**」と旧記述を残していた。
- **D-14 の実消費（edges 上）**: P-2-5 のみが `→D-14` を持つ。P-3 系に `→D-14` 辺は存在しない。だが D-14 本文の消費先列は「P-2-5・**P-3（カバレッジ点検・発火制御）**」と旧記述を残していた。
- **処置**: D-9・D-14 の消費先列から旧「P-3（カバレッジ点検・発火制御）」記述を削除し、実 edges に一致する消費 P へ修正した（D-9 →「P-1-4・P-2-5」、D-14 →「P-2-5」、発火制御一元化＝P-2-5・DD-12(b) の注記を添えた）。記述修正に加えバックリファレンス辺付与による edges 構造変更があるため D-9・D-14 ともに MINOR バンプ v0.1→v0.2。

---

**付記（G9・INFO）**: D-9 と D-18（属性検査ビュー）がいずれも `scheduled` という同名語を含むが出自が異なる。D-9 の `scheduled` は config.yaml の **phases リスト（有効スプリント名・scheduled 値ドメイン照合用）**由来であり、D-18 の `scheduled` は各**ノードのフロントマター scheduled 属性（フェーズ限定発火指定）**由来である。前者はドメイン（許容値集合）、後者は個々のノードの指定値で、別概念。独立ノード化はしない（INFO 軽微）。io.md の D-9・D-18 本文に出自区別の注記を追記済み。

**指摘時 ref_version**:
- P-2-2-3 "0.1"（processes.md・P-2-2-3 ノードバッジ v0.1 時点）
- D-9 "0.1"（io.md・D-9 ノードバッジ v0.1 時点）
- D-14 "0.1"（io.md・D-14 ノードバッジ v0.1 時点）
- SPEC-15-1 "0.1"（spec.md・SPEC-15-1 ノードバッジ v0.1 時点）

**対応状況**: resolved

**対応内容**: reconciliation が次を反映済み。
- **G1**: P-2-2-3 に `→SPEC-15-1`（ref_version "0.1"）を付与し SPEC-15-1 の孤児を解消（P-2-2-3 MINOR バンプ v0.1→v0.2）。
- **G4**: D-9 の消費先列から旧「P-3（カバレッジ点検・発火制御）」を削除し「P-1-4・P-2-5」へ修正、D-14 の消費先列から旧「P-3」を削除し「P-2-5」へ修正（発火制御一元化＝P-2-5・DD-12(b) の注記を添える。D-9・D-14 ともに MINOR バンプ v0.1→v0.2）。
- **G9 付記**: io.md の D-9・D-18 本文に `scheduled` 同名語の出自区別注記を追記。
- **バックリファレンス**: 処置対象ノード（P-2-2-3・D-9・D-14・SPEC-15-1）へ `→FND-94` バックリファレンス辺を付与済み。SPEC-15-1 は処置の被覆対象（孤児解消の主題ノード）として、P-2-2-3・D-9・D-14 は記述修正対象として、いずれも実在するため付与先あり。指摘時バッジ（v0.1）から MINOR バンプした P-2-2-3・D-9・D-14 は現バッジ v0.2 を ref_version とし、SPEC-15-1 は v0.1 据置（ref_version "0.1"）。

> **孤立回避メモ**: 本 FND-94 は forward 依存辺を処置対象 4 ノード（P-2-2-3・D-9・D-14・SPEC-15-1）へ持つため孤立しない（RULE-005 該当なし）。各処置対象が `→FND-94` バックリファレンスを張り返すことでバックリファレンス整合も成立する。

---

## FND-95: P-4-4「終了コード決定」の終端出力（終了コード 0/1）が O/D ノード化されず価値経路が受け手に到達しない（PR6 価値経路の穴）

<details><summary>⬡ FND-95 · v0.1.0</summary>

```yaml
id: FND-95
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: P-4-4
    ref_version: "0.2.0"
```
</details>

**深刻度**: WARNING

**内容**: P-4-4（終了コード決定）の唯一の終端出力「終了コード（0 または 1・SPEC-25-2/25-3）」が O ノード（系外アクタ宛出力）にも D ノード（内部データ）にも台帳化されておらず、本文では「終了コード（0 または 1）を生成」と散文記述されているだけで、受け手へ到達する辺が存在しない。終了コードは CI ゲート（ACTOR-2＝CI/レビュアー側）が違反有無をプログラム的に判定するための提供価値であり、P-4-4 の「提供価値: CI ゲート実現・自動パイプラインが違反有無をコードで判定できる」が、台帳上は出力ノード→受け手への連続経路として接続されていない。すべての入力がプロセスを通って価値（出力）まで連続して届くこと（PR6）に反し、終端で価値経路が遮断されている既存欠陥である。FND-93（D-4 入力の台帳上断絶）と同類の「図では暗黙に流れる想定だが台帳が経路を表現していない」価値経路の穴であり、PR #27 のレビューで顕在化した。

**対応状況**: resolved

**対応内容**: reconciliation が次により断絶を解消した。
- **O-6「終了コード」新設**: 系外アクタ（ACTOR-2＝CI ゲート/レビュアー）宛の出力ノード O-6（type: O・「終了コード」）を io.md に起票した。O-6 は SPEC-25-2（ERROR あり→終了コード 1）・SPEC-25-3（ERROR なし→終了コード 0）への依存辺を持ち、生成元 P-4-4 への辺（O→P・ref_version "0.2"）と受け手 ACTOR-2 への到達（O→ACTOR）を成立させ、終端の価値経路を接続する。終了コードの実生成リーフは P-4-4 であり、リーフ先例（O-3→P-7-2）に倣い生成元辺を親 P-4 ではなく終端リーフ P-4-4 に張った。
- **P-4-4 本文の更新**: P-4-4 の出力本文「終了コード（0 または 1）を生成」を「O-6（終了コード 0/1）を生成——O-6 が生成元 P-4-4 に依存（O→P）」へ更新し、散文の終端出力を O ノード生成として台帳化した（P-4-4 MINOR バンプ v0.1→v0.2）。
- **バックリファレンス付与**: 処置対象 P-4-4 は実在する（付与先あり）ため、P-4-4 に `→FND-95`（ref_version "0.2"）バックリファレンス辺を付与した。FND-93/FND-94 の resolved 先例（処置対象本体が実在＝付与先ありの場合は処置対象へ backref を張り、FND 側の forward 辺と張り合わせて二重辺を許容）に倣い、FND-95→P-4-4（forward）と P-4-4→FND-95（backref）を併存させる。FND-95→P-4-4 の ref_version は P-4-4 改訂後バッジ v0.2 に揃えた。

**指摘時 ref_version**: P-4-4 "0.1"（03-processes.md・P-4-4 ノードバッジ v0.1 時点）

> **孤立回避メモ**: 本 FND-95 は forward 依存辺を処置対象 P-4-4 へ持つため孤立しない（RULE-005 該当なし）。P-4-4 が `→FND-95` バックリファレンスを張り返すことでバックリファレンス整合も成立する。

---

## FND-96: 設計層の接続チェーン DM→MOD→D が欠落しており MOD→P / DM→P の強制が PR1 違反を生む

<details><summary>⬡ FND-96 · v0.5.0</summary>

```yaml
id: FND-96
type: FND
labels: []
scheduled: ""
suppress: []
resolved: true
edges: []
```
</details>

**深刻度**: WARNING

**改訂理由（MINOR バンプ v0.4→v0.5）**:
Q-4 選択肢A 採用（DD-16）により `fnd_lifecycle` 専用ルールが正式定義されたため、暫定措置の `suppress: [RULE-006]` を撤去し `resolved: true` で機械判定可能にする。本 FND は既に元 forward 辺を削除し（`edges: []`）処置対象 MOD-1（v0.2）から `→FND-96`（backward 辺）を受けており、新 `fnd_lifecycle` の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘内容・深刻度・対応状況（resolved）は不変（suppress 撤去＋`resolved` フィールド追加＝構造変更のため MINOR バンプ）。

**改訂理由（MINOR バンプ v0.3→v0.4）**:
選択肢A（DM→MOD→D 正規化・フル実施）を sprint-1 で適用・完了し、対応状況を resolved に更新。実施した処置は以下のとおり。(1) `config.yaml` の `MOD → P`（必須・単一ターゲット）を `MOD → [P | D]`（OR）へ変更し、`DM → P` を `DM → MOD` へ変更（`DM → TERM` は維持）。(2) MOD-1 の `→P-1` 辺を削除し、realize するデータ型概念 D-4・D-6・D-9〜D-21 への辺へ変更（MOD-1 を MINOR バンプ v0.1→v0.2・`→FND-96` バックリファレンス付与）。(3) TERM-1〜4（NodeRecord / EdgeRecord / ViolationRecord / ConfigSlice）を新設。(4) DM-1〜4（各型の DM ノード・`→TERM` + `→MOD-1`）を新設。指摘対象・深刻度は変更しない（処置完了の記録のため MINOR バンプ）。MOD-1 が `→FND-96` を張り返すため FND-96 自体の forward 辺（`→MOD-1`）は削除し、`suppress: [RULE-006]` を付与（resolved FND の辺逆転ルール）。指摘時 ref_version は本文に記録済み（DD-3）。

**改訂理由（MINOR バンプ v0.2→v0.3）**:
オーナーが選択肢A（DM→MOD→D 正規化・フル実施）・実施スプリント sprint-1 を決定。
対応状況を「選択肢A 確定（sprint-1 実施予定）」に更新。
設計修正（config.yaml・MOD-1 辺変更・DM/TERM ノード著作）は別コミットにて実施。

**改訂理由（MINOR バンプ v0.1→v0.2）**:
v0.1 は「MOD-1 が `MOD→P` を張っているのは category error」という**局所的な指摘**に留まっていた。オーナーとの議論で、本質は設計層の**接続チェーン構造ごと誤っている**点（正しくは `DM → MOD → D`）にあると確認された。これに伴い、(1) タイトルを接続チェーン欠落の問題として書き直し、(2) 正しいチェーン `DM→MOD→D` の説明・PORT→MOD パターンとの対比を追加、(3) 現状 config.yaml の誤り（`DM→P`／`MOD→P` 単一ターゲット）を2点明記、(4) 選択肢 A/B/C を DM→MOD→D 正規化を軸に改訂した。指摘対象・edges・深刻度・対応状況は変更しない（内容拡充のため MINOR バンプ）。

**内容**:
`config.yaml` の必須辺 `{ node: MOD, target: P, activate_stage: design, severity: error, reason: "MODはプロセスを実装" }`（L44）は **「全モジュールはプロセスを実装する」と暗黙に仮定**している。しかし設計層には**プロセスを実装しないモジュール**（データ型を定義するモジュール）が存在し、本来あるべき接続チェーン **`DM → MOD → D`** が欠落している。

**正しいチェーン（オーナー確認済み）**:

```
DM（型定義: NodeRecord 等）
  → MOD（モジュールファイル: domain.py）
      → D（ランタイムのデータ概念: D-4 構造化ノードセット 等）
```

- `DM → MOD`：型定義はモジュールに属す。これは既存の **`PORT → MOD`**（ポート Protocol 定義はモジュールに属す）と同じ接続パターンであり、設計層は既にこの「定義要素 → モジュール」の向きを採用している。
- `MOD → D`：データ型モジュールは D（ランタイムのデータ概念）を実現する。
- 処理（ユースケース）モジュールは `MOD → P` で正しい（MOD-2〜9・13〜18 は現状維持）。

**現状 config.yaml の誤り（2点）**:
1. `DM → P`（必須）：DM は直接 P を指すのでなく **MOD を介すべき**。`DM → MOD` に変更が必要（`DM → TERM` は維持）。
2. `MOD → P`（必須・単一ターゲット）：データ型モジュールは P でなく **D を実現**するため、単一ターゲット強制が誤り。`MOD → [P | D]`（OR）が正しい。

この2点の強制により、データ型モジュール（MOD-1）は本来 realize すべき**データ D を指せず**、発生源（プロセス P）の辺で代用せざるを得ない。これは **PR1「もの＋発生源で分ける」違反**——データ（もの）をプロセス（発生源）の辺で表現する category error である。

- **MOD-1（domain）**：責務は「NodeRecord / EdgeRecord / ViolationRecord / ConfigSlice 等の値オブジェクトを定義する」＝**データ型の定義のみ**。プロセスを実装しない。にもかかわらず `MOD-1 → P-1`（ノード受付・パース）の辺を便宜的に張っており、本来は `MOD-1 → D`（自分が realize するデータ）であるべきところを、`MOD→P` 単一強制のために P の辺で表している。

MOD-1 が定義するデータ型と分析層 D の対応:
- NodeRecord / EdgeRecord ↔ **D-4（構造化ノードセット）**
- ViolationRecord ↔ **D-6（RULE 違反リスト）**
- ConfigSlice ↔ **D-9〜D-16（config 各スライス）**
- 消費スライス値オブジェクト ↔ **D-17〜D-21（検査ビュー）**

追跡性は損なわれない：分析層に既に `D → P`（内部データは生成プロセスに依存・config L37）があるため、`DM → MOD-1 → D → P` で型→設計→分析→プロセスの追跡経路が連続する（PR6 を満たす）。

**主たる指摘対象**: MOD-1（domain.py）

**同種の影響ノード（併記）**:
- **MOD-10（ports.py）**：FileSystemPort Protocol を定義（PORT-1 を実現・被参照あり）。プロセスでない。現状 `→P-1` は便宜的。PORT 型定義の辺設計は別途精査（選択肢A 参照）。
- **MOD-11（adapters/fs.py）**：FileSystemPort を実装するアダプタ。プロセスでない。現状 `→P-1`。アダプタは独立概念として別途精査。
- **MOD-12（__main__.py）**：合成ルート＋CLI。ORC-1/E-1 を実現すべき結線役。現状 `→P-5` は恣意的。合成ルートは独立概念として別途精査。
- ユースケース系（MOD-2〜9・MOD-13〜18）の `→P` は責務とプロセスが一致しており**正しい**＝本指摘の対象外。

**指摘時 ref_version**: MOD-1 "0.1"（01-modules.md v 時点）／MOD-10 "0.1"／MOD-11 "0.1"／MOD-12 "0.1"（いずれも 01-modules.md v 時点）

**深刻度判定の根拠**:
機械 RULE（MOD→P＝RULE-006）は MOD-1/10/11/12 とも `→P` 辺を保持しており**現状は充足**しているため、検証ツール上の live な ERROR 違反は発生していない。一方で、これは「ルールが満たされているのに辺の意味と接続チェーン構造が原則と食い違う」**設計層の構造的な原則違反（PR1 category error・DM→MOD→D チェーンの欠落）**であり、放置すると設計→分析の追跡が誤った相手（P）を指し続ける。既存の構造的・原則違反 FND の判定（live RULE 失敗を伴わない原則違反は WARNING）に倣い **WARNING** と判定する。

**選択肢（オーナー判断）**:

- **選択肢A（採用・DM→MOD→D 正規化・フル実施）**：
  - `config.yaml`：`MOD → [P | D]`（OR）へ変更、`DM → P` を `DM → MOD` へ変更（`DM → TERM` は維持）。
  - MOD-1 の edge を D-4・D-6・D-9〜16・D-17〜21 へ変更。
  - DM ノードを新設（NodeRecord・EdgeRecord・ViolationRecord・ConfigSlice 等 → MOD-1 + 対応 TERM）。
  - TERM ノードを新設（各型に対応する用語定義）。
  - MOD-10・11・12 の辺設計も別途精査（PORT 型定義・アダプタ・合成ルートはそれぞれ別概念）。
  - 根拠：PR1・追跡性が最も完全。設計層の全レイヤー（DM→MOD→D）が揃う。
  - コスト：TERM + DM ノードの新規著作が必要（分量あり）。

- **選択肢B（中間・ルール修正＋MOD-1 辺変更のみ）**：
  - `config.yaml`：`MOD → [P | D]`（OR）へ変更、`DM → P` を `DM → MOD` へ変更。
  - MOD-1 の edge を D へ変更。
  - DM・TERM ノードの新設は後続スプリントへ繰り越し。
  - 根拠：ルールの意味的誤りを今すぐ解消し、DM/TERM の著作は後続で行う。最小変更で config 整合を先行できる。
  - コスト：DM/TERM ノードが存在しない間は `DM→MOD` ルールが事実上発火しない（発火開始ステージが design であるため DM ノード著作まで RULE は待機状態）。

- **選択肢C（現状維持）**：
  - 据え置き。原則違反（DM→MOD→D チェーンの欠落・PR1 category error）が残る。

**推奨**: **A**。B は中間として成立するが、`DM→MOD` ルールに対応するノード（DM）が存在しない状態が続く。A の TERM + DM ノード著作は作業量があるが、設計層の完全性（PR6・DM→MOD→D の連続）のために必要。C は違反据え置きとなる。実施スプリントはオーナー判断（`scheduled` は空のまま）。

**対応状況**: resolved

**対応内容**（選択肢A 適用・sprint-1 完了）:
- **config.yaml**（`docs/doc-system/config.yaml`）：必須辺 `{ node: MOD, target: P, ... }` を `{ node: MOD, target: [P, D], ... }`（OR・reason: "MODはプロセスを実装（処理系）またはデータ型を実現（D）"）へ変更。`{ node: DM, target: P, ... }` を `{ node: DM, target: MOD, ... }`（reason: "DM型定義はモジュールに属す（DM→MOD→D チェーン）"）へ変更。`DM → TERM` は維持。
- **MOD-1**（`doc-system/05-design/01-modules.md`）：`→P-1` 辺を削除し、realize するデータ型概念へ辺を変更（D-4 "0.2"・D-6 "0.1"・D-9 "0.2"・D-10〜13 "0.1"・D-14 "0.2"・D-15〜21 "0.1"）。`→FND-96`（ref_version "0.3"）バックリファレンス辺を付与。MINOR バンプ v0.1→v0.2。
- **TERM-1〜4 新設**（`doc-system/03-analysis/05-terms.md`）：TERM-1 NodeRecord・TERM-2 EdgeRecord・TERM-3 ViolationRecord・TERM-4 ConfigSlice の用語定義を著作。
- **DM-1〜4 新設**（`doc-system/05-design/04-domain-model.md`）：DM-1 NodeRecord型・DM-2 EdgeRecord型・DM-3 ViolationRecord型・DM-4 ConfigSlice型群を著作（各 `→TERM` + `→MOD-1`）。
- これにより設計層の接続チェーン `DM → MOD → D` が確立し、MOD-1 はデータ（もの）を D の辺で表現するようになった（PR1 category error 解消）。追跡経路 `DM → MOD-1 → D → P` が連続し PR6 を満たす。
- バックリファレンス辺は処置対象 MOD-1（v0.2）側に reconciliation 反映時に付与済み。FND-96 自体の edges は MOD-1 が張り返すため現状維持（`→MOD-1` のみ）。

## FND-97: ORC-1 frontmatter の P 辺が DD-15 決定に反する（解消済み）

<details><summary>⬡ FND-97 · v0.2.0</summary>

```yaml
id: FND-97
type: FND
labels: []
scheduled: ""
suppress: []
resolved: true
edges: []
```
</details>

**改訂理由（MINOR バンプ v0.1→v0.2）**:
Q-4 選択肢A 採用（DD-16）により `fnd_lifecycle` 専用ルールが正式定義されたため、暫定措置の `suppress: [RULE-006]` を撤去し `resolved: true` で機械判定可能にする。本 FND は処置対象 ORC-1（v0.4）から `→FND-97`（backward 辺）を受けており、新 `fnd_lifecycle` の resolved ルール（backward 必須・forward 不在期待・`edges: []`）を満たす。指摘内容・深刻度・対応状況（resolved）は不変（suppress 撤去＋`resolved` フィールド追加＝構造変更のため MINOR バンプ）。

> **深刻度**: WARNING ／ **対応状況**: resolved（選択肢A 適用・ORC-1 v0.4 で P 辺削除）

**指摘時 ref_version**: ORC-1 "0.3"（03-orchestration.md の ORC-1 バッジ v0.3 時点）

### 指摘内容

ORC-1（検査パイプライン実行）の frontmatter が DD-15 の決定と正面衝突している。

**DD-15 影響範囲の決定文**（`doc-system/04-verification/04-decisions.md`）:
> 「ORC-1 に `→E-1` 辺を追加（MINOR バンプ v0.1→v0.2）。`→DD-15` バックリファレンス付与。**従来の P への参照は本文で実行段として表現する**。」

**実体の ORC-1 frontmatter**（`doc-system/05-design/03-orchestration.md` v0.3）:
```yaml
edges:
  - to: E-1       # ← 正しい（DD-15 で追加された起動イベント辺）
  - to: DD-15     # ← 正しい（バックリファレンス辺）
  - to: P-5       # ← DD-15 決定に反する（除去すべき辺）
  - to: P-6       # ← 同上
  - to: P-1       # ← 同上
  - to: P-2       # ← 同上
  - to: P-3       # ← 同上
  - to: P-4       # ← 同上
```

さらに ORC-1 の改訂理由（v0.1→v0.2）が「P ノードへの辺は実行する段の列挙として**維持**」と書いており、DD-15 の「本文で実行段として表現する」と正面から矛盾する。

### 原則

- **PR4（矛盾は停止して打ち上げ）**: DD-15 の決定記録と ORC-1 実体の不一致。両立しない事実は勝手に解決せず起票してから処置する。
- **DD-15 の根拠**: 「MOD→P で実装関係は既出・ORC→P は同軸重複」。ORC の本質は起動イベント（E）への参照であり、P への辺は ORC の固有情報を持たない（実行段は本文で表現可能）。

### 選択肢

- **選択肢A（推奨・採用）**: ORC-1 frontmatter の P 辺（→P-5/P-6/P-1/P-2/P-3/P-4）を削除。実行段は本文「フロー」節（既に散文で列挙済み）で表現する。ORC-1 を MINOR バンプ（v0.3→v0.4）。DD-15 の決定に従う。
- **選択肢B**: P 辺を「実行順序辺」として明示的に残す設計とするなら、DD-15 影響範囲・ORC-1 改訂理由・SKILL.md の注記（「ORC→P が重複」）を「P 辺は順序辺として保持する」に改訂し、記述を一致させる。B は DD-15 を部分的に覆す再決定（DD バンプ）が必要。

### 推奨と処置

**A を採用**。DD-15 の意思決定（ORC→P は同軸重複）を尊重するのが整合的。B は DD-15 を部分的に覆す再決定を要する。

**処置（選択肢A 適用・解消と同時起票）**:
- `doc-system/05-design/03-orchestration.md`: ORC-1 frontmatter から P 辺6本（→P-5/P-6/P-1/P-2/P-3/P-4）を削除。残辺は `→E-1`・`→DD-15` のみ。実行段の列挙は本文「段の目的」「フロー」「実行順序の不変条件」節で散文として表現済み（既存記述で充足）。MINOR バンプ v0.3→v0.4（辺削除＝構造変更）。改訂理由（v0.1→v0.2）本文の「P ノードへの辺は実行する段の列挙として維持」を「P への参照は本文の実行段で表現（DD-15 準拠で frontmatter 辺は削除）」へ訂正。
- ORC-1（処置対象ノード）に `→FND-97` バックリファレンス辺を付与する（resolved 化に伴うバックリファレンス）。

> **resolved 同時起票の根拠**: 解消と同コミット（sprint-1）で処置するため resolved として著作。バックリファレンス辺は処置対象 ORC-1 v0.4 側に reconciliation 反映時に付与する。

## FND-98: ダッシュボード・PR 本文が DD-13 v0.2 改訂前のスナップショットで陳腐化

<details><summary>⬡ FND-98 · v0.2.0</summary>

```yaml
id: FND-98
type: FND
labels: []
scheduled: ""
suppress: []
resolved: true
edges: []
```
</details>

**改訂理由（MINOR バンプ v0.1→v0.2）**:
Q-4 選択肢A 採用（DD-16）により `fnd_lifecycle` 専用ルールが正式定義されたため、暫定措置の `suppress: [RULE-006]` を撤去し `resolved: true` で機械判定可能にする。本 FND は処置対象 DD-13（v0.3）から `→FND-98`（backward 辺）を受けており、新 `fnd_lifecycle` の resolved ルール（backward 必須・forward 不在期待・`edges: []`）を満たす。指摘内容・深刻度・対応状況（resolved）は不変（suppress 撤去＋`resolved` フィールド追加＝構造変更のため MINOR バンプ）。

**深刻度**: WARNING

**内容**: ダッシュボード（doc-system/00-dashboard.md）と PR #28 本文が、DD-13 v0.2 改訂（MOD 粒度を C 案へ・MOD-1〜18 へ拡張）・DD-15 追加・ORC-2 新設を反映しておらず、旧スナップショット（DD-13 v0.1・MOD-1〜12・ORC-1 のみ）のまま陳腐化している。DD-13 の決定内容がダッシュボード上で誤って表現されている（ダッシュボードは trace_scope.exclude で out-of-graph のため、誤表現の原因ノードである DD-13 を edges.to 先とする）。PR #27 ② と同種のドキュメント陳腐化の再発。

陳腐化していた箇所（4 箇所）:
1. ダッシュボード DD-13 サマリ行（🧭 DD / Q / PEND サマリ）: 「MOD 粒度：L1 親プロセス単位（B 案）＋P-2-5 例外。MOD-1〜12 で採用（2026-06-16）」のまま。
2. ダッシュボード直近作業 N2 行（🔄 直近の作業）: 「MOD-1〜12 / … / ORC-1 著作・反映。DD-13/DD-14 起票」のまま。
3. ダッシュボード完了済み行（🔥 推奨ネクストアクション > 完了済み）: 「N2（… MOD-1〜12/…/ORC-1 著作・DD-13/DD-14 … 2026-06-16）」のまま。
4. PR #28 本文: タイトル・本文が「MOD-1〜12 … ORC-1 … DD-13/DD-14」のままで MOD-13〜18 / ORC-2 / DD-15 / DD-13 v0.2 が未記載。

**対応状況**: resolved

**対応内容**: 解消と同時起票。ダッシュボード 3 箇所（DD-13 サマリ行・直近作業 N2 行・完了済み行）を DD-13 v0.2（C 案・MOD-1〜18・2026-06-20）・DD-15・ORC-2 を反映した記述へ更新済み。PR #28 本文は GitHub 側で更新済み。指摘の原因ノード DD-13 に `→FND-98` のバックリファレンス辺を付与する（reconciliation 反映時）。

## FND-99: 設計接続規則の決定（FND-96・DD-15）が out-of-graph 著作資産に未伝播

<details><summary>⬡ FND-99 · v0.2.0</summary>

```yaml
id: FND-99
type: FND
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

**深刻度**: WARNING

**対応状況**: resolved（解消と同コミットで処置済み・sprint-1。ただし**バックリファレンス対象が未著作のため意図的にエラー発火状態を保持**＝下記「バックリファレンスの扱い」「孤立エラーの意図的保持」を参照）

**改訂理由（MINOR バンプ v0.1→v0.2）**:
オーナー決定に従い、resolved FND の辺逆転ルール（DD-3・処置対象→FND の被参照辺へ張り直し・元 forward 辺は削除・指摘時 ref_version は本文へ移動）を本 FND にも適用し、辺の扱いを明確化した。具体的には、(1) v0.1 が残していた元の forward 辺（`→FND-96` ref "0.4"・`→DD-15` ref "0.1"）を削除して `edges: []` とし、指摘時 ref_version は本文の「指摘時 ref_version」節に維持・明確化する。(2) 本 FND の処置対象は 7 つの out-of-graph 著作資産（ノードでない）であり、バックリファレンス（対象→FND-99）の張り先が現時点で存在しないため、FND-99 は outgoing/incoming 辺をともに持たず孤立し、抑制不可（RULE-005＝always_error）のエラーを発火する。(3) **このエラーは恣意的に抑制しない**（`suppress` を付けない）＝「resolved だがバックリファレンス対象が未著作」を正しく示すシグナルとして意図的に保持する旨を本文に明記する。指摘内容・深刻度・対応した同期資産リストは変更しない（辺の扱いと記述の明確化のための MINOR バンプ）。

### 内容

設計層の接続規則を変更する決定（FND-96・DD-15）が、`config.yaml`（機械判定の正本）には反映されているものの、その規則を人間/LLM 向けに表現する out-of-graph の著作資産（スキル・エージェント定義・接続マトリクス等）には伝播していなかった。著作資産が config と食い違ったまま放置されると、次回 design-author がノードを著作する際に**旧ルールの誤った辺を再生産する**。FND-98（DD-13 改訂後のダッシュボード/PR 本文の陳腐化）と同種の「決定の非伝播」ドリフト。

ドリフトしていた規則は2系統:

1. **FND-96（MOD/DM 規則・2026-06-20）**: `MOD → P`（単一）→ 正しくは `MOD → [P | D]`（OR）。`DM → P` → 正しくは `DM → MOD`（DM→MOD→D チェーン）。
2. **DD-15（ORC 規則・2026-06-18）**: `ORC → P` → 正しくは `ORC → E`（起動イベント参照）。architecture-design スキルには反映済みだったが、他の著作資産に未伝播だった。

### 深刻度判定の根拠

`config.yaml`（機械判定の正本）は既に正しいため、検証ツール上の **規則内容に起因する** live な RULE 違反は発生しない（out-of-graph 資産は `trace_scope` 対象外）。一方、著作ガイドが正本と食い違うと誤った辺の再生産を招くため、FND-98 と同じく構造的・運用上のドリフトとして **WARNING**。

> 注: 本 FND が現在発火している RULE-005（完全孤立）エラーは、上記の指摘内容（規則の非伝播・WARNING）とは別物であり、「resolved だがバックリファレンス対象が未著作」という FND ライフサイクル上のシグナルである（下記参照）。深刻度 WARNING は指摘内容そのものの評価であって、孤立エラーの severity（RULE-005＝error・always_error）とは独立である。

### 対応内容

解消と同時起票。以下7資産を `config.yaml` の正ルールに同期（FND-96 の `MOD→[P|D]`／`DM→MOD`、DD-15 の `ORC→E`）:

- `.claude/skills/architecture-design/SKILL.md`（MOD 必須辺）
- `.claude/skills/domain-model/SKILL.md`（DM 必須辺・TERM→SPEC 補正）
- `.claude/skills/orchestration-design/SKILL.md`（ORC 必須辺）
- `.claude/agents/design-author.md`（MOD/ORC/DM 行）
- `.github/agents/design-author.agent.md`（MOD/ORC/DM 行）
- `docs/doc-system/03-connection-matrix.md`（mermaid＋接続要否マトリクス MOD/DM/ORC 行）
- `docs/doc-system/01-document-items.md`（MOD/DM/ORC 上流参照）

> **バックリファレンスの扱い（オーナー決定・v0.2）**: FND-99 の**処置対象は上記7資産（いずれも out-of-graph・ノードでない）**ため、`対象 → FND-99` のバックリファレンス辺を張る先のノードが**現時点では存在しない**。オーナー決定に従い、**設計・実装が進めばこれらの規則を実体化するノード（例: 接続マトリクス・著作ガイドに対応する設計/実装ノード）が著作され、その時点でバックリファレンス対象が生まれる。それまでは恣意的な抑制を行わず、エラー発火状態を保持する**（`suppress` を付けない）。辺逆転ルール（DD-3）に従い、元の forward 辺（`→FND-96`・`→DD-15`）は v0.2 で削除し、指摘時 ref_version は下記「指摘時 ref_version」節に記録する。FND-96・DD-15 は本指摘の subject であって処置対象ではないため、両ノードの版・辺は変更しない（本 FND から両ノードへの forward 辺も張らない）。

> **🔴 孤立エラーの意図的保持（恣意的抑制の禁止）**: 上記の結果、FND-99 は outgoing 辺（forward を削除済み）も incoming 辺（バックリファレンス対象が未著作）も持たず**完全に孤立**し、**RULE-005（完全孤立＝in/out 辺が0本・always_error・抑制不可）のエラーを発火する**。これは欠陥ではなく、**「FND-99 は resolved だが、その処置（規則の著作資産への伝播）を引き受けるべきバックリファレンス対象ノードがまだ著作されていない」という状態を正しく示す意図的なシグナル**である。RULE-005 は always_error（`suppress`・`scheduled`・`activate_stage` いずれでも抑制不可）であり、恣意的に抑制することはできず、またオーナー決定によりすべきでない。設計・実装フェーズで対応するノードが著作され、`対象 → FND-99` のバックリファレンス辺が張られた時点でこの孤立エラーは自然に解消する。それまでは本エラーを**意図的に保持**する。

### 指摘時 ref_version

FND 解消時に辺が逆向きに張り直され（対象→FND）元の forward 辺（FND→対象）が削除されるため、辺情報から指摘時の版が失われる。本文に明記する（DD-3 制度化）。本 FND は処置対象が out-of-graph 資産でバックリファレンス対象が未著作のため辺がすべて失われており、以下が指摘時の版の唯一の証跡である。

- **FND-96 "0.4"**（02-findings.md の FND-96 バッジ v0.4 時点・MOD/DM 規則変更の出所）
- **DD-15 "0.1"**（04-decisions.md の DD-15 バッジ v0.1 時点・ORC 規則変更の出所）
- DD-13 "0.2"（04-decisions.md の DD-13 バッジ v0.2 時点・MOD 粒度 C 案の決定文脈。FND-98 と同コミットで処置した際の関連版）

---

## FND-100: 設計層の被覆チェーン DM→MOD→D が D-5/D-7/D-17〜D-21 経路で非対称（解消済み）

<details><summary>⬡ FND-100 · v0.2.0</summary>

```yaml
id: FND-100
type: FND
labels: []
scheduled: ""
suppress: []
resolved: true
edges: []
```
</details>

**改訂理由（MINOR バンプ v0.1→v0.2）**:
Q-4 選択肢A 採用（DD-16）により `fnd_lifecycle` 専用ルールが正式定義されたため、暫定措置の `suppress: [RULE-006]` を撤去し `resolved: true` で機械判定可能にする。本 FND は処置対象 MOD-1・DM-3・DM-5・DM-6 から `→FND-100`（backward 辺）を受けており、新 `fnd_lifecycle` の resolved ルール（backward 必須・forward 不在期待・`edges: []`）を満たす。指摘内容・深刻度・対応状況（resolved）は不変（suppress 撤去＋`resolved` フィールド追加＝構造変更のため MINOR バンプ）。

**深刻度**: WARNING

**対応状況**: resolved（オーナーが本セッションで即時実施を承認済み＝独断繰り越しではない。`scheduled` は空のまま）

### 内容

FND-96（DM→MOD→D 正規化・選択肢A・sprint-1）の処置後、**MOD-1↔DM の被覆が非対称**であり、接続チェーン `DM → MOD → D` が一部経路で途切れている（PR6 連続性の部分残存）。

- **MOD-1（domain）が realize 宣言する D**（v0.2 時点の edges）: D-4・D-6・**D-9〜D-21**。
- **新設済み DM（DM-1〜4）が realize する D**: D-4（DM-1/DM-2）・D-6（DM-3）・**D-9〜D-16（DM-4）** のみ。
- → **D-17〜D-21（各検査ビュー型）に対応する DM 型ノードが存在しない**。これらは D-4 の単なる部分集合ではなく、D-4 に無い計算フィールド（in_degree / out_degree 等）を持つ**別の値オブジェクト型**であり、domain.py 上に独立した型が要る。DM 不在のため `DM → MOD → D` チェーンが D-17〜D-21 経路で途切れている。

加えて同じ非対称が次の 2 点に現れる:

1. **D-5（パース段違反リスト）**: D-6（RULE 違反リスト）と完全に同形（`list[ViolationRecord]`）であるにもかかわらず、MOD-1 は D-6 のみ realize し D-5 を realize していなかった（MOD-1↔D の非対称）。型は同一の「もの」（違反レコード 1 件）であり、発生源差（パース段 P-1 / RULE 検査段 P-2）は生成元プロセスの差として D ノード側で既に表現済み。
2. **D-7（カバレッジ計測結果）**: CoverageReport 型が MOD-1・DM のどちらにも不在で、`DM→MOD→D` チェーンが D-7 経路で完全に欠落していた。

**対象外**: D-22（グラフトポロジビュー）は `labels:[post-mvp]` のため本指摘の対象外。

**主たる指摘対象**: MOD-1（domain.py）。被覆漏れの所在は MOD-1 の realize 辺集合と新設 DM 群の被覆の差にある。

### 指摘時 ref_version

FND 解消時に辺が逆向きに張り直され（対象→FND）元の辺（FND→対象）が削除されるため、辺情報から指摘時の版が失われる。本文に明記する（DD-3 制度化）。

- **MOD-1 "0.2"**（01-modules.md・MOD-1 バッジ v0.2 時点。realize 辺が D-4/D-6/D-9〜D-21 で D-5/D-7 を欠く状態）
- 補足対象の指摘時バッジ（被覆漏れの相手側の版も provenance として記録）:
  - DM-3 "0.1"（04-domain-model.md・D-5 を未 realize の状態）
  - DM-4 "0.1"（04-domain-model.md・D-17〜D-21 に対応する DM が DM-4 の外に存在しない状態）
  - D-5 / D-7 / D-17〜D-21 "0.1"（02-io.md）

### 深刻度判定の根拠

機械 RULE 上、MOD-1 は `MOD → [P | D]`（OR・RULE-006）を D 辺で充足済みであり、新設 DM 群も `DM → MOD`・`DM → TERM` を充足している。被覆が非対称でも個々のノードは必須辺を満たすため、検証ツール上の live な RULE 失敗は発生しない。本件は「各ノードのルールは満たされているが、`DM → MOD → D` チェーンの被覆が一部経路で途切れる」**設計層の構造的な被覆漏れ（PR6 連続性の部分残存）**であり、FND-96（live RULE 失敗なし・WARNING）の判定基準に倣い **WARNING** と判定する。

### 対応内容（design-author 著作の DM/TERM/MOD 補完を反映）

被覆の非対称を是正するため、以下を著作・反映した:

1. **DM-3（ViolationRecord 型）v0.1→v0.2**: 「実現する D」に **D-5（パース段違反リスト）を追加**（D-6 と同形・新規型なし）。`→MOD-1` ref_version を MOD-1 更新後バッジ "0.3" に追従。`→FND-100` 付与。
2. **TERM-5・DM-5（CoverageReport）新設**: D-7 の FR×condition カバレッジテーブル部を表す novel 型。D-7 の網羅性穴リスト部は引き続き DM-3（ViolationRecord）が担う協働。MOD-17 が `measure_spec_coverage(...) -> CoverageReport` で型名を命名済み。DM-5 に `→FND-100` 付与。
3. **TERM-6・DM-6（InspectionViews 型群）新設**: **D-17〜D-21 を 1 ノードで一括 realize**。先例 DM-4（ConfigSlice 型群）と射影系として構造一致。MOD-13 が `project_views(node_set) -> InspectionViews` で集約戻り値型を命名済み。DM-6 に `→FND-100` 付与。
4. **MOD-1 v0.2→v0.3**: realize 辺に **D-5・D-7 を追加**（各 D 現バッジ "0.1"）。D-17〜D-21 は既存辺あり。`→FND-100` バックリファレンス付与（FND-100 の forward 辺を逆転した辺）。

これにより設計層の被覆が対称化し、`DM → MOD → D` チェーンが D-5（DM-3）・D-7（DM-5＋DM-3）・D-17〜D-21（DM-6）の全経路で連続する（PR6 充足）。

> **バックリファレンスの扱い**: 処置対象 MOD-1・DM-3・DM-5・DM-6 はいずれも実在ノード（付与先あり）のため、各ノードに `→FND-100`（ref_version "0.1"）を付与済み。削除済みの処置対象はなく「付与先なし」項目は該当なし。D-5/D-7/D-17〜D-21（D ノード側）には本対応で `→FND-100` を張らない（被覆の主体は MOD-1 realize 辺と DM 群であり、FND-96 でも D ノード側には張らず MOD-1 が張り返した先例に倣う）。

> **config.yaml 規則変更なし**: 本対応は既存規則（`DM→TERM`・`DM→MOD`・`MOD→[P|D]`・`TERM→SPEC`）に準拠するノード著作のみで config.yaml の `must_link_to`/`must_be_linked_from` を変更しない。よって out-of-graph 著作資産への規則伝播チェック（FND-99 パターン）は不要。

> **🟡 注記（決定済みトレードオフ・新規是正対象でない）**: PR #32 は `MOD → [P | D]` の OR 化により「ドメイン型モジュール → D／処理モジュール → P」の型別強制が機械判定で効かなくなる点（処理モジュールが誤って D のみを張っても RULE-006 上は合格）を 🟡 として挙げている。これは FND-96 選択肢A（オーナー承認済み・config.yaml L44）で織り込み済みのトレードオフであり、本 FND-100 の新規是正対象ではない。設計レビュー（人/LLM）・asset-auditor・spec-inspector の点検でカバーする運用前提。独立追跡のための別ノード化（INFO FND/DD・subject `→FND-96`・config.yaml L44 所在）はオーナー判断に委ねる（独断で起票も「対応不要」も結論づけない）。

---

## FND-101: resolved 済み FND（FND-1〜95）が元の forward 辺を削除せず辺逆転ルールに違反している

<details><summary>⬡ FND-101 · v0.1.0</summary>

```yaml
id: FND-101
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: Q-4
    ref_version: "0.1.0"
```
</details>

**深刻度**: WARNING

**対応状況**: open（未是正・修正は別ブランチで別途実施。今回は FND 起票のみ）

**指摘時 ref_version**: Q-4 "0.1"（05-questions.md の Q-4 新規バッジ v0.1 時点・本 FND の是正方針が依存する FND 専用ライフサイクルルールの未決論点）

### 内容

resolved 済み FND の大部分（**FND-1〜FND-95** の範囲）が、解消後も元の forward 辺（FND → 処置対象）を削除しておらず、FND の辺逆転ルール（DD-3／verification-author 規約）に違反している。

**辺逆転ルール（正しい resolved FND の形）**:
- 処置対象ノード側に `対象 → FND-x` の被参照辺（バックリファレンス）を張る。
- FND 側の元の forward 辺（FND → 対象）は**削除**する。
- 指摘時 ref_version は辺から失われるため、FND 本文に明記して移動する（DD-3）。

**現状（Read で確認した違反パターン）**:
FND-1〜95 の resolved FND では、処置対象側へのバックリファレンス付与（`対象 → FND-x`）は概ね行われている一方で、**FND 側の元 forward 辺（FND → 対象）が削除されずに残置されている**。すなわち「対象 → FND」と「FND → 対象」の**双方向辺が併存**し、辺逆転（forward を消して backward へ張り替える）が完了していない。汎用ルール `{ node: FND, target: any }`（config.yaml L60・通称 RULE-006・forward 必須）が forward 辺の残置を許す（むしろ要求する）ため、live な RULE-006 エラーは発生せず、違反が機械検知されないまま蓄積している。

今回 sprint-1 で起票・処置した **FND-96 / FND-97 / FND-98 / FND-100 は是正済み**（元 forward 辺を削除し `edges: []` とし、暫定 `suppress: [RULE-006]` を付与）。FND-99 も辺逆転を適用済み（out-of-graph 処置対象のため孤立エラーを意図的に保持）。一方で **FND-1〜95 は未是正**のまま残っている。

### 範囲のサンプリング根拠（軽量サンプリング・全件精査は別ブランチ作業）

`doc-system/04-verification/02-findings.md` の冒頭側 resolved FND を Read でサンプリングした結果、以下のように元 forward 辺が残置されている（バックリファレンスは別途対象側に付与済み・double-edge 状態）:

- **FND-2**（resolved・P-2 を分解）: `edges: [→P-2 (ref "0.2")]` が残置。本文に「P-2 に `→FND-2` バックリファレンス辺を付与済み」とあり、双方向辺が併存。
- **FND-4**（resolved・SPEC-29/30 新設・P-3 分解）: `edges: [→P-3 (ref "0.2")]` が残置。本文に「P-3・SPEC-29・SPEC-30 に `→FND-4` バックリファレンス辺を付与済み」とあり併存。
- **FND-5**（resolved・FR-6 本文修正）: `edges: [→FR-6 (ref "0.2")]` が残置。本文に「FR-6 に `→FND-5` バックリファレンス辺を付与済み」とあり併存。
- **FND-1**（resolved・ACTOR-3 削除）: `edges: [→P-1 (ref "0.2"), →FND-16 (ref "0.1")]` が残置（処置対象 ACTOR-3 は削除済みだが forward 辺は張替先 P-1 を指したまま残る）。

サンプル4件すべてで「forward 辺残置＋対象側バックリファレンス付与」の double-edge パターンが確認でき、FND-1〜95 全体に同パターンが広く分布していると推定される（範囲の網羅的確定は別ブランチ作業）。対照的に FND-96/97/98/100 は `edges: []`（forward 削除済み）であり、是正済みと未是正の境界が明確。

### 深刻度判定の根拠

**WARNING** と判定する。根拠:
- **live な機械 RULE 失敗は発生していない**: 残置された forward 辺はむしろ汎用 RULE-006（FND→any・forward 必須）を充足してしまうため、検証ツール上のエラーは出ない（違反が機械検知されない＝サイレントな構造的負債）。
- **誤った辺が検証グラフ・トレースに与える影響は構造的・運用的**: resolved FND の本来の意味は「処置対象から指される（過去の指摘の証跡）」であるべきところ、forward 辺が残ることで「FND が依然として対象を指す＝未解消であるかのような」誤った接続がグラフに残る。トレース・被覆解析（どのノードがどの指摘で処置されたか／逆にどの FND が生きているか）を辿る際に double-edge が誤読・ノイズを生む。
- 既存の構造的・原則違反 FND（live RULE 失敗を伴わない構造的ドリフトは WARNING＝FND-96/98/99/100 の判定基準）に倣い **WARNING** とする。ERROR にしないのは、価値経路の遮断や機械判定の誤った合否（fail-open）を直接引き起こすものではなく、トレース可読性・構造整合性の劣化に留まるため。

### 是正方針（Q-4 の決定に依存）

本 FND の是正方針は **Q-4（FND 専用ライフサイクルルールを汎用 RULE-006 から独立定義すべきか）の決定に依存する**ため、subject 辺として `→Q-4`（ref_version "0.1"）を張る。

- Q-4 で **選択肢A（FND 専用ライフサイクルルールを config に独立定義）** が採択された場合、resolved FND は「対象 → FND の backward 必須・forward 不在期待」が機械判定されるようになる。その規則に合わせて FND-1〜95 の元 forward 辺を一括削除し、指摘時 ref_version を各 FND 本文へ移動する是正を行う（FND-96/97/98/100 で用いた暫定 `suppress: [RULE-006]` も Q-4 決定後は不要になり撤去対象）。
- Q-4 が別案（運用ルールのみ／現状維持）に決した場合は、その決定に整合する形で是正方針を確定する。
- いずれにせよ、是正の具体手順・対象範囲（FND-1〜95 の網羅的確定）・実施は **Q-4 決定後に別ブランチで実施**する。本ノートは範囲を本文で説明するに留め、処置対象ノードの網羅的列挙（FND-1〜95 すべてへの辺）は行わない（範囲が広く double-edge の機械検知も別途要するため）。

> **代表対象を Q-4 1 辺に限定した理由**: 本 FND の対象は FND-1〜95 と広範であり、処置対象を辺として列挙すると 90 件超の辺が必要になる一方、是正方針自体が Q-4 の決定待ちで未確定である。よって RULE-005（非孤立）・RULE-007（実在 ID 参照）を満たしつつ、是正の依存先である Q-4 を subject 辺として 1 本張り、対象範囲は本文で説明する方針とした。

> **オーナー指示・スケジュール**: 修正は別ブランチで別途実施するため、今回は FND 起票のみに留める。実施スプリント（`scheduled`）は空のままとし、Q-4 決定後にオーナーが判断する（独断でのスプリント繰越は禁止＝CLAUDE.md「スケジュール独断禁止」）。AI が独断で「対応不要」「将来検討でよい」と結論づけない（PR7・独断禁止）。

---

## FND-102: 必須辺（config 44 行）のうち dedicated SPEC を持つのは 8 行のみ・行→被覆 SPEC のトレーサビリティが不在

<details><summary>⬡ FND-102 · v0.2.0</summary>

```yaml
id: FND-102
type: FND
labels: []
scheduled: ""
edges:
  - to: SPEC-8
    ref_version: "0.2.0"
  - to: FND-79
    ref_version: "0.1.0"
```
</details>

**深刻度**: INFO

**根拠（深刻度確定の理由）**: issue #30 の点検の結論として **完全な起票漏れ（挙動を規定する SPEC の不在）は存在しない**。必須辺の機械判定 RULE-006 の挙動は SPEC-8「必須上流辺の欠如」（condition: failure・親 FR-3）が parametric な傘仕様として config 44 行すべてを一般則でカバーしており、ツール挙動は定義済み（ERROR ではない）。残る課題は「dedicated（テスタブル）SPEC への昇格基準が未文書化」「config 行→被覆 SPEC のトレーサビリティ表が不在」というドキュメント整備・テスト被覆の均一化の論点であり、現時点の実害はゼロ。同根の既存指摘 **FND-79（open・INFO「RULE-006/025/026 が複数 SPEC に分散→索引化」）** と性質が一致するため、決定の一貫性を保つ意味でも INFO に揃える。なお「将来 config 行を追加した際に SPEC 追従漏れを機械検知できない」リスクは WARNING 寄りだが、これは現状の欠陥ではなく将来の運用機構の話であり、INFO の推奨（トレーサビリティ表・昇格基準の明文化）で吸収できると判断した。

**対応状況**: resolved（2026-06-21・オーナー決定＝選択肢②「全 44 行を dedicated SPEC 化」を実施）

**対応内容**: 必須辺 config 44 行のうち dedicated SPEC を欠いていた 36 行に対し、行固有・テスタブルな子 SPEC（各 condition: failure〔SPEC-28-3 のみ normal・post-mvp〕・「当該 node が必須辺を欠くとき RULE-006 を config 行の severity で報告」を単一アサーション化）を新設した。内訳：

- **SPEC-56**（傘・親 FR-3）＋ SPEC-56-1〜8（要件層 8 行：SR→VAL／FR→SR／NFR→SR／SPEC→[FR,NFR,SPEC]／VAL←[SR]／SR←[FR,NFR,ACTOR]／FR←[SPEC]／NFR←[SPEC]）
- **SPEC-57**（傘・親 FR-3）＋ SPEC-57-1〜12（分析層 残 12 行：ACTOR→SR／TERM→SPEC／I→SPEC／O→SPEC／O→ACTOR／D→SPEC／D→P／P→SPEC／E→SPEC／E→ACTOR／ACTOR←[E,I,O]／D←[P]。価値経路 3 種 O→P・I←P・E←P は既存 SPEC-30 が担う）
- **SPEC-58**（傘・親 FR-3）＋ SPEC-58-1〜12（設計層 12 行：ORC→E／DS→P／MOD→[P,D]／DM→TERM／DM→MOD／PORT→MOD／PRS→DS／SCM→SPEC／CFG→SCM／CFG→SPEC／PROMPT→SPEC／E←[ORC]）
- **SPEC-18-6〜8**（既存傘 SPEC-18 を拡張・検証層 3 行：TD→SPEC／TR→TC／TD←[TC]）
- **SPEC-28-3**（既存傘 SPEC-28 を拡張・実装層 1 行・post-mvp：SRC→[DM,PORT,ORC]）

これで 44 行すべてが dedicated SPEC を持ち（既存 8 行＝SPEC-30-1/2/3・SPEC-15-1・SPEC-18-2/3/4/5 ＋ 新設 36）、各 SPEC 本文の `入力/トリガ` に対応 config 行を明記したため「config 行→被覆 SPEC」のトレーサビリティが 1:1 で成立した（昇格基準の論点も全行昇格により解消）。一般則 SPEC-8 は parametric な傘仕様として併存し、新設子はその個別ケースの位置づけ。（PR #34 レビュー対応：origin/main マージで config が fnd_lifecycle 版＝標準 44 行に更新されたため、当初の 45 行/既存 9 の計数を 44 行/既存 8 へ訂正。FND→any は `must_link_to` から `fnd_lifecycle.unresolved.must_link_to` へ移動し標準 44 行の対象外となった。）

**バックリファレンス**: 処置の中心である新設傘 SPEC-56／SPEC-57／SPEC-58 に `→FND-102` 辺を付与済み（検証層 SPEC-18-6〜8・実装層 SPEC-28-3 は既存傘の拡張のため、代表 backref は本 3 傘が担い、本文で全 36 子を列挙）。**forward 辺（→SPEC-8／→FND-79）は baseline 慣行どおり保持**し、辺逆転（resolved FND の forward 削除）は FND-101／Q-4 の決定に依存する別ブランチ処置の対象として同一コホートに属する。

> **残課題（別件）**: 形式的な「config 行→SPEC」索引表（人間可読の一覧）は FND-79（RULE-006/025/026 の分散→索引化・open・INFO）の領分として別途検討。本 ② 実施で RULE-006 の dedicated SPEC はさらに増えたため、FND-79 の索引化要望はむしろ強まる（FND-79 のクローズはオーナー判断）。

**指摘時 ref_version**: SPEC-8 "0.2"（doc-system/04-verification 配下 SPEC-8 ノードバッジ x.y 基準・DD-8 時点）／FND-79 "0.1"（doc-system/04-verification/02-findings.md の FND-79 ノードバッジ v0.1 時点）

### 内容

issue #30「必須辺の仕様化漏れ点検」として、コミット済み baseline の `docs/doc-system/config.yaml` の必須接続定義（`must_link_to` 31 行＋`must_be_linked_from` 13 行＝計 **44 行**・いずれも機械判定は RULE-006）が SPEC に網羅されているかを点検した。

**結論：完全な起票漏れはない。** 44 行すべての挙動は SPEC-8 の一般則（「RULE-006 をその config 行の severity（error/warning）で報告する」）が parametric にカバーする。正常系の通過は SPEC-5（構造違反 0 通過）・SPEC-17（検証層）・SPEC-29-1（分析層）が担う。

ただし **dedicated（行固有・テスタブル）SPEC を持つのは 44 行中 8 行のみ** で、被覆が大きく非対称になっている。

| config 行 | 種別 | dedicated SPEC |
|---|---|---|
| O→P | must_link_to | SPEC-30-1 |
| I←[P] | must_be_linked_from | SPEC-30-3 |
| E←[P] | must_be_linked_from | SPEC-30-2 |
| SPEC←[TD] | must_be_linked_from | SPEC-15-1 |
| TC→TD | must_link_to | SPEC-18-4 |
| TC←[TR] | must_be_linked_from | SPEC-18-2 |
| NFR←[FND,TC,VERIFY] | must_be_linked_from | SPEC-18-3 |
| VERIFY→any | must_link_to | SPEC-18-5 |

※ FND→any（SPEC-18-1）は main の Q-4→DD-16 で `fnd_lifecycle.unresolved.must_link_to` へ移動したため標準 44 行の対象外。fnd_lifecycle 系の dedicated 化は FND-103 で追跡（本 PR スコープ外）。

残り **36 行** は SPEC-8 一般則のみに依存し dedicated SPEC を持たない（要件骨格 8 行・分析層 12 行・設計層 12 行・実装/検証 4 行）。

### 論点

1. **昇格基準が未文書化**: どの行を dedicated（テスタブル）SPEC へ昇格するかの基準が文書化されておらず、現状は価値経路 3 種（O→P・I←[P]・E←[P]）＋検証層のみが ad-hoc に dedicated 化されている。
2. **トレーサビリティ表が不在**: config 行 → 被覆 SPEC の対応表が存在しないため、「必須辺の仕様化漏れ」を機械的に確認できない（＝issue #30 が懸念した状態そのもの）。
3. **FND-79 と同根**: 「同一 RULE が複数 SPEC に分散しているため索引化が必要」という FND-79（open・INFO）の指摘を、必須辺被覆の観点から具体化・補強する位置づけ。

（補足：SPEC-30 本文は「D の接続漏れは一般則 SPEC-8 でカバー、SPEC-30 は価値経路の名前付き 3 種のみ列挙」と明記。SPEC-48 は NFR-5「USDM 1 段制約＝祖先辺の禁止」であり、必須辺の欠如〔RULE-006〕とは別軸のため本点検の対象外。`fnd_lifecycle`（resolved.must_be_linked_from／must_not_link_to）の dedicated SPEC 化は FND-103 として別途追跡（本 PR は標準 44 行に限定）。）

### 推奨（オーナー提示用・3 案）

- **① 現状維持＋FND-79 索引化のみ（最小工数）**: SPEC-8 一般則で挙動規定済みとみなし、config 行→SPEC 対応を索引（connection-matrix 拡張等）で可視化するに留める。
- **② 全 44 行を dedicated・テスタブル SPEC 化（網羅最大・重い）**: 1 アサーション 1 SPEC を厳格適用。網羅は最大化するが SPEC が +36 で重く、SPEC-8 と内容が重複する。
- **③ トレーサビリティ表＋昇格基準の明文化（中庸・推奨）**: config 各行→covering SPEC 対応表を追加し、「どの行を dedicated 化するか」の基準（例：価値経路に面する辺・severity=error・新規型導入時）を明文化する。漏れの機械確認を可能にしつつ SPEC 爆発を回避できる。FND-79 の索引化要望とも両立する。

> 推奨は ③ だが、実施スプリント（今スプリント実施 vs 次スプリント繰り越し）の判断はオーナーに委ねる。独断で `scheduled` を設定しない（スケジュール独断禁止）。

### config.yaml 規則変更チェック（FND-99 パターン）

本 FND は **既存の必須辺定義の被覆状況を点検した指摘であり、`must_link_to`/`must_be_linked_from` などの接続規則の追加・変更・削除を含まない**。よって out-of-graph 著作資産（接続マトリクス・ドキュメント一覧・各 author エージェント／スキル）への規則伝播チェックは不要。推奨 ③ を採択して索引・対応表を整備する場合は、その整備時に connection-matrix／document-items 等への反映を別途検討する（本 FND 起票時点では伝播対象なし）。

---

## FND-103: fnd_lifecycle の必須辺ルール3つのうち resolved 系2ルールに dedicated SPEC が不在（被覆均一化の残課題）

<details><summary>⬡ FND-103 · v0.1.0</summary>

```yaml
id: FND-103
type: FND
labels: []
scheduled: ""
edges:
  - to: SPEC-18-1
    ref_version: "0.1.0"
  - to: FND-102
    ref_version: "0.2.0"
```
</details>

**深刻度**: INFO

**根拠（深刻度確定の理由）**: 現状 SPEC-8 の parametric 一般則（「RULE-006／必須辺欠如をその config 行の severity で報告」）と config の `fnd_lifecycle` 定義そのものが3ルールすべての挙動を規定済みで、機械判定上の挙動は定義済み・実害ゼロ。残る課題は「fnd_lifecycle 系の3ルールのうち resolved 系2ルールが dedicated（行固有・テスタブル）SPEC を欠き、被覆が不均一」というドキュメント／テスト被覆均一化の論点に留まる。FND-102（issue #30 本体）が標準必須辺44行を全て dedicated 化した結果、相対的に fnd_lifecycle 系の dedicated 欠如が目立つ位置づけになったが、これは現状の欠陥ではなく被覆均一化の整備論点であるため、同根の FND-79（RULE 分散→索引化・open・INFO）・FND-102（INFO）と決定の一貫性を保ち **INFO** とする。

**対応状況**: open（2026-06-22 起票）

### 内容

main の Q-4→DD-16（commit 52093ed）で `config.yaml` に正式化された FND ライフサイクルルール `fnd_lifecycle` は、必須辺ルールを3つ定義する:

| fnd_lifecycle ルール | 辺の向き | severity | dedicated SPEC |
|---|---|---|---|
| `unresolved.must_link_to`（FND→any） | forward 必須 | error | **SPEC-18-1（被覆済み）** |
| `resolved.must_be_linked_from`（any→FND） | backward 必須 | error | **不在** |
| `resolved.must_not_link_to`（FND→any 不在期待） | forward 不在期待 | warning | **不在** |

`unresolved.must_link_to`（FND→any）は SPEC-18-1「FND に被指摘要素への辺欠如（RULE-006）」が dedicated 被覆するが、`resolved.must_be_linked_from`（any・error＝resolved FND は処置対象からの backward 辺必須）と `resolved.must_not_link_to`（any・warning＝resolved FND の元 forward 辺は削除済みであること）には dedicated（行固有・テスタブル）SPEC が存在しない。

issue #30 が目指した「config 行→被覆 SPEC の 1:1 トレーサビリティ台帳」を fnd_lifecycle 系にも広げるなら、この resolved 系2ルールの dedicated SPEC 化が残課題として残る。

### 位置づけ（スコープ境界）

- issue #30（FND-102）は **標準必須辺44行**（`must_link_to` 31＋`must_be_linked_from` 13）に限定して全行 dedicated 化したため、`fnd_lifecycle` 系3ルールは FND-102 の対象外（オーナー決定）。本 FND-103 がその残課題を別途追跡する。
- FND-101／Q-4 の **辺逆転コホート**（resolved FND の forward 削除・backward 付与）と同一系統。resolved 系2ルール（must_be_linked_from／must_not_link_to）はまさに辺逆転後の resolved FND の構造を機械判定するルールである。
- FND-79（RULE-006/025/026 が複数 SPEC に分散→索引化・open・INFO）とも同根で、「同一 RULE 系の被覆均一化・索引化」という横断課題の一部。

### 推奨（オーナー提示用・2 案）

- **① 現状維持**: SPEC-8 の parametric 一般則＋config の `fnd_lifecycle` 定義自体で挙動は規定済みであり、行固有 SPEC を起こさない。fnd_lifecycle 系の可視化は索引化論点（FND-79 の領分）に委ねる。
- **② resolved 系2ルールに dedicated SPEC を新設**: `resolved.must_be_linked_from`（any・error）と `resolved.must_not_link_to`（any・warning）に行固有・テスタブルな SPEC（SPEC-18 傘の拡張等）を新設し、fnd_lifecycle 系も config 行→SPEC の 1:1 台帳に組み込む。被覆は均一化するが SPEC が +2 増え、SPEC-8 一般則と内容が一部重複する。

> 推奨は実施時期を含めオーナー判断に委ねる。現状実害ゼロ（INFO）のため独断で `scheduled` を設定しない（スケジュール独断禁止・CLAUDE.md）。AI が独断で「対応不要」「将来検討でよい」と結論づけない（PR7・独断禁止）。

**指摘時 ref_version**: SPEC-18-1 "0.1"（doc-system/02-what/03-spec.md の SPEC-18-1 ノードバッジ v0.1 時点）／FND-102 "0.2"（doc-system/04-verification/02-findings.md の FND-102 ノードバッジ v0.2 時点）。なお被指摘対象の `fnd_lifecycle` 定義は `docs/doc-system/config.yaml`（DD-16・Q-4 から昇格・main commit 52093ed）に存在するが、config.yaml はノード化されないため辺は張れず、本文で参照を明記する（SPEC-18-1＝fnd_lifecycle の被覆済みルールを forward 辺の代表対象とした）。

### config.yaml 規則変更チェック（FND-99 パターン）

本 FND は **`fnd_lifecycle` の既存ルールの dedicated SPEC 被覆状況を指摘するもので、`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` 等の接続規則の追加・変更・削除を含まない**（規則自体は main の Q-4→DD-16 で既にコミット済み・本 FND はその被覆論点を起票するのみ）。よって out-of-graph 著作資産（接続マトリクス・ドキュメント一覧・各 author エージェント／スキル）への規則伝播チェックは不要。推奨 ② を採択して dedicated SPEC を新設する場合は、その整備時に spec-author／connection-matrix 等への反映を別途検討する（本 FND 起票時点では伝播対象なし）。

---

## FND-104: ノードバージョンの桁数定義が 2パート（x.y）と 3パート（x.y.z）で矛盾し DD-8 §4 の z バンプが実行不能

<details><summary>⬡ FND-104 · v0.1.0</summary>

```yaml
id: FND-104
type: FND
labels: []
scheduled: ""
suppress: []
edges: []
```
</details>

**深刻度**: ERROR

**対応状況**: open（オーナー判断待ち・`scheduled: ""`）

> **辺の扱い（open 段階）**: 本 FND は open（未決・処置未着手）であり、指摘対象（FR-1・DD-8・DM-1 等）への forward 辺をまだ確定させていない。現時点では `edges: []` で起票し、処置方針（案 A）がオーナー承認された時点で指摘対象への forward 辺を付与する（FND-99/102/103 と同じ open 起票パターン）。`edges: []` のため RULE-005（完全孤立・always_error）が発火するが、これは「open だが対象辺未確定」というシグナルであり恣意的に抑制しない（`suppress` なし）。

### 内容

ノードバージョンの**桁数定義が文書間で 2パート（`x.y`＝MAJOR.MINOR）と 3パート（`x.y.z`＝MAJOR.MINOR.PATCH）で矛盾**しており、DD-8 §4 のバンプルールが現状のノードでは実行不能なデグレ状態にある。

| 箇所 | 記述 | 形式 |
|---|---|---|
| FR-1（要件） | `x.y.z`、z は不問 | **3パート** |
| DD-8 タイトル | 「ノードバッジをノード固有バージョン（x.y.z）に正式化」 | **3パート** |
| DD-8 選択肢 A | 「バッジ＝ノード固有の x.y.z バージョン（MAJOR.MINOR）として正式化」 | **矛盾（x.y.z と MAJOR.MINOR を混在）** |
| DD-8 §1 決定 | `⬡ PREFIX-N · vX.Y` の `X.Y` をノード固有バージョン（MAJOR.MINOR）として正式化 | **2パート（← ここが根因）** |
| DD-8 §4 バンプルール | 内容のみ → z バンプ（`x.y.Z`）／構造変更 → MINOR（`x.Y`）／大規模 → MAJOR（`X.y.z`） | **3パートを前提** |
| ドメインモデル（DM-1） | `ref_version は x.y 形式` | 2パート |
| 現実の全ノード（約510件） | `0.1`・`0.2`・`0.3`… | 2パート（デグレ状態） |

### 根本原因

DD-8 の決定テキストで `x.y.z（MAJOR.MINOR）` と括弧書きした際に「`x.y.z` = `MAJOR.MINOR` = 2パート」という混同が発生した。MAJOR.MINOR は本来 2 要素（`x.y`）だが、`x.y.z` という 3 要素表記と同一視してしまい、その結果 §1 で「`vX.Y`（MAJOR.MINOR）」と 2パートを正式化してしまった。

しかし DD-8 §4 のバンプルールは「内容のみ変更 → z バンプ（`x.y.Z`）／z バンプは伝播不要（依存元の ref_version 更新不要）」という設計であり、これは**第3パート（z=PATCH）の存在を前提**としている。z バンプは「ref_version ドリフトを誘発しない軽微改訂」を実現する仕組みだが、現在の全ノードが 2パート（`x.y`）で運用されているため、**z バンプを実行する桁が存在せず、§4 のルールが実行不能**になっている。

### 影響範囲

1. **FR-1 との矛盾（ERROR）**: 要件 FR-1 は `x.y.z`（3パート・z 不問）を定義しているが、DD-8 §1・ドメインモデル・現実ノードは 2パート。要件と設計・実態が直接矛盾している。
2. **DD-8 §4 の z バンプルールが実行不能**: 「内容のみ → z バンプ」「z バンプは伝播不要」という ref_version ドリフト抑止の中核機構が、2パート運用下では適用できない。本来 z バンプで済む軽微改訂が MINOR バンプを誘発し、不要な ref_version 伝播を引き起こすデグレ。
3. **ドメインモデル（DM-1「ref_version は x.y 形式」）の訂正が必要**: 機械判定上の ref_version 桁数定義も 3パートへ訂正が要る。
4. **out-of-graph 著作資産・スキル・エージェント・接続マトリクスへの横展が必要**: DD-15／FND-99 の前例に従い、版定義を記述する全資産を同期する必要がある（後述の案 A 横展対象）。

### 処置案（案 A のみ・オーナー承認後に実施）

**案 A（3パート x.y.z に統一）**:

全ノードバージョンを `x.y` → `x.y.0` に移行し、DD-8 §1・ドメインモデル（DM-1）・既存スキル/エージェント/authoring-guide 等の参照箇所を 3パート（`x.y.z`）に訂正する。これにより FR-1（`x.y.z`）・DD-8 §4（z バンプ前提）・実態の三者が一致し、z バンプによる ref_version ドリフト抑止機構が実行可能になる。

**横展対象（DD-15／FND-99 の前例に従い必須）**:
本案は版定義（桁数）という記法ルールの変更を含むため、機械判定の正本（config.yaml の DD-8 注記）だけでなく、版定義を人間/LLM 向けに表現する out-of-graph 著作資産・著作規律資産にも漏れなく同期する。漏れると次回著作時に旧定義（2パート）の版が再生産される（FND-99 パターン）。

- `docs/doc-system/` 配下の out-of-graph 資産：
  - `04-notation.md`（バッジ・版表記の説明）
  - `02-meta-schema.md`（ノードバージョニング §1・RULE-004 ドリフト定義 §7）
  - `07-authoring-guide.md`（著作規律・版バンプ手順）
  - `05-verification.md`（RULE-004 判定基準）
  - `config.yaml`（DD-8 注記・RULE-004 説明コメント）
  - `03-connection-matrix.md`・`01-document-items.md`（版・ref_version 記述があれば）
- `.claude/` 配下のスキル・エージェント（著作規律で版バンプ／ref_version 桁数を記述しているもの）を `Grep` で漏れなく点検・訂正。
- ドメインモデル DM-1（`ref_version は x.y 形式` → `x.y.z 形式`）。

> **接続規則変更の伝播チェック（本 FND での扱い）**: 本案は config.yaml の `must_link_to`/`must_be_linked_from`（接続規則）そのものは変更しないが、版定義（桁数・バンプ）という著作規律ルールを変更するため、FND-99 と同型の「決定の非伝播」ドリフトを防ぐ必要がある。上記横展は open 段階では計画として記載するにとどめ、案 A がオーナー承認された時点で各資産を点検・訂正し、処置内容に同期資産リストを記録する。

**推奨**: **案 A を即時実施**。理由：(1) FR-1（要件）が既に 3パートを定義しており、要件に実態・設計を合わせるのが筋である。(2) DD-8 §4 の z バンプ機構（ref_version ドリフト抑止）は 3パート前提で設計されており、これを活かすには 3パート化が必須。(3) 移行コストは `x.y → x.y.0` の機械的付与であり、ノード改訂履歴の情報は失われない（既存 `x.y` がそのまま `x.y.0` になる）。

### 指摘時 ref_version

FND 解消時に edges が逆転（FND→対象 → 対象→FND）し指摘時の版が辺情報から失われるため、本文に明記する（DD-3 制度化）。本 FND は open のため辺は未確定だが、指摘対象とその版を以下に凍結記録する。

- **FR-1 "0.1"**（doc-system/02-what/01-fr.md・FR-1 ノードバッジ v0.1 時点。`x.y.z`・z 不問を定義）
- **DD-8 "0.1"**（doc-system/04-verification/04-decisions.md・DD-8 ノードバッジ v0.1 時点。§1 で 2パート `vX.Y` を正式化・§4 で 3パート前提の z バンプを規定する矛盾の所在）
- **DM-1 "0.1"**（ドメインモデル・`ref_version は x.y 形式` と 2パートを規定）

---
