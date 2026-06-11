---
version: "0.1.0"
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
**対応状況**: open
**対応内容**: （推奨）ACTOR-3 を削除し、spec-inspector を系内処理（P-1〜P-4）へ一本化するのが第一案。残存参照 ACTOR-3→SR-4 については、SR-4 が他から支持されているため孤児化しない。代替案＝ACTOR-3 を残して駆動辺を補う案は「駆動される側＝系内」と意味が合わず非推奨。**オーナー判断待ち（要件フェーズのため暫定修正はしない）。**

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
    ref_version: "0.4"
```
</details>

**深刻度**: WARNING
**内容**: P-2 が構造完結性（RULE-005〜008）・ドリフト（RULE-001/002/004/022）・カバレッジ（RULE-016〜019）・検証層（RULE-006/020/021）の全 RULE 群を1プロセスに内包している。対応 SPEC が SPEC-5〜23 と多数に分かれているのに、P-2 だけがそれらを束ねており、DFD レベリング上の単一責務の疑いがある。
**対応状況**: open
**対応内容**: （推奨）段階①ドリフト／②構造完結性／③カバレッジ で P-2 を子プロセス（P-2-1..）へ分解する案を検討。オーナー判断待ち。

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
**対応状況**: open
**対応内容**: （推奨）欠番の経緯を確認し、(a) 意図的削除なら本文に理由を残す、(b) CI 駆動が別事象なら E-2 を復活させる。オーナー判断待ち。

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
    ref_version: "0.4"
```
</details>

**深刻度**: WARNING
**内容**: P-3「カバレッジ点検」本文は「孤児ノード・未駆動出力・未定義反応」（グラフ網羅性点検）と「SPEC×condition×TD」の2系統を担うが、P-3 の依存先は SPEC-14 のみである。前者のグラフ網羅性点検に対応する SPEC が spec.md に存在せず、FR/SPEC の裏付けがない機能が分析層に出現している＝価値経路の上流欠落（PR6）。
**対応状況**: open
**対応内容**: （推奨）グラフ網羅性点検の SPEC を FR-6（または FR-3）配下に新設するか、P-3 から当該責務を除去して整合させる。オーナー判断待ち。

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
**対応状況**: open
**対応内容**: （推奨）FR-6 本文の「RULE-015」を「RULE-006（被依存 `SPEC←[TD]`・旧 RULE-015）」へ修正。低リスクな記述整合だが、要件本文のためオーナー確認のうえ反映。

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
    ref_version: "0.4"
```
</details>

**深刻度**: INFO
**内容**: suppress(I-2)/scheduled(I-3)/ref_version(I-4) を I-1（ノードファイル）と独立の入力に割っているが、いずれも著者がノードファイル内に書く値で、発生源・もの（ファイル）が同一である。PR1（もの＋発生源で分ける／使い道だけで割らない）に照らすと過分割の疑いがある。ただし各々が別 SPEC（SPEC-22/20/9）に紐づき追跡価値はある。
**対応状況**: open
**対応内容**: （推奨）要件段では現状維持（追跡価値が分割コストを上回る）。設計段で DM/CFG に落とすときに再評価。info 据え置き。
