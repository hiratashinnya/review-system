---
version: "0.1.0"
---
# N0 再点検 — SPEC 品質強化バッチの検証記録と全グラフ走査の副次発見

> **型**: VERIFY / FND / Q ／ **必須**: 対象要素への依存辺が1本以上（RULE-006 config: `→ any`）
> 無名依存辺のみ（`kind`/`status` なし・`to` は単数・全辺に `ref_version` 必須）。
> Q-1 は出力先 `04-verification/05-questions.md`（reconciliation が新設・version 0.1.0）。

## VERIFY-2: N0（SPEC 品質強化分）再点検の実施記録

<details><summary>⬡ VERIFY-2 · v0.1</summary>

```yaml
id: VERIFY-2
type: VERIFY
labels: []
scheduled: ""
suppress: []
edges:
  - to: FR-11
    ref_version: "0.2"
  - to: FR-13
    ref_version: "0.2"
  - to: FR-14
    ref_version: "0.2"
  - to: SPEC-31
    ref_version: "0.3"
  - to: SPEC-40
    ref_version: "0.3"
  - to: FND-16
    ref_version: "0.1"
  - to: FND-17
    ref_version: "0.1"
  - to: Q-1
    ref_version: "0.1"
```
</details>

**検証手法**: メインスレッドによる全 doc-system ノードの自動整合走査（id/edge 抽出スクリプト）＋目視裏取り。
**実施日**: 2026-06-12
**対象範囲**: requirements 層の SPEC 品質強化バッチ（FR-11 改訂・FR-13/14 新設・SPEC-1/2/26/27 書き直し・SPEC-31〜40 新規・condition 語彙 empty・パース検証 RULE-023〜027）を重点に、全層（VAL/SR/FR/NFR/SPEC/ACTOR/I/O/D/P/E/VERIFY/FND/DD/PEND）の参照整合・ref_version・カバレッジ・FND バックリファレンス対称性を点検。

**結果（重点バッチ）**: 合格。新規/改訂ノードについて、
- (a) FR への依存辺は全て実在・ref_version="0.2" 一致、
- (b) SPEC→親 SPEC 辺なし（全て FR 直参照）、
- (c) FR-11/13/14 のカバレッジ（normal＋failure）充足、FR-9/10/12/14 の normal 単独は suppress[RULE-018]/scheduled:post-mvp で説明可、
- (d) condition 語彙は normal/boundary/empty/failure/error に収まり empty は SPEC-31 のみで正用、
- (e) FND-12〜15 のバックリファレンス（FR-1→FND-12・SPEC-31→FND-13・SPEC-1/2/26/27→FND-14・FR-11→FND-15）対称。

**SPEC 品質強化バッチに新規ギャップなし**。

**結果（全グラフ走査の副次発見）**: 既存層に整合崩れを検出 → FND-16（RULE-007 ERROR）・FND-17（RULE-004 ドリフト群 WARNING）・Q-1（凍結記録のドリフト扱いの設計論点）を起票。

**発生した指摘**: → FND-16・FND-17・Q-1 を参照。

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
**対応状況**: open
**対応内容（推奨）**: FND-1 の forward 辺を、ACTOR-3 の役割を吸収した在グラフノードへ張り替える。**推奨＝P-1（ノード受付・パース＝spec-inspector 系内処理の代表）** に `to: P-1` で再接続し、P-1 に `→FND-1` バックリファレンスを付与。代替案：旧 ACTOR-3 の上流だった SR-2 に再接続。要件フェーズのためオーナー判断を仰ぐ（暫定で張り替えない）。

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
- (c) 解消済み FND-2→P-2("0.5"→0.6)・FND-3→E-1("0.4"→0.5)・FND-4→P-3("0.5"→0.6)、義務辺 PEND-1→I-2("0.5"→0.6) がドリフト。
- (d) 付随：FND-3 の forward 辺が E-1 を指すが、当該指摘の処置（E-3→E-2 リネーム）の back-ref は E-2 に付与されており、forward/back の対象ノードが不一致（FND-3 は本来 E-2 を指すべき疑い）。

**対応状況**: open
**対応内容（推奨）**: current_stage を analysis へ進める段（ダッシュボード N1）で一括解消する。「生きた」依存辺（E/O→ACTOR の "0.2"→"0.3"、FND-3 forward の E-1→E-2＋"0.5"）は再点検のうえ ref_version 更新。「凍結記録」（VERIFY-1、解消済み FND-2/4）の扱いは Q-1 の決定に従う。requirements フェーズでは分析層を据え置き、本 FND で追跡のみ。

---

## Q-1: 凍結記録（VERIFY・解消済み FND）の ref_version ドリフト扱い

**status: open**

<details><summary>⬡ Q-1 · v0.1</summary>

```yaml
id: Q-1
type: Q
labels: []
scheduled: ""
suppress: []
edges:
  - to: VERIFY-1
    ref_version: "0.1"
```
</details>

**論点**: VERIFY ノードや解消済み FND など「ある時点の状態をレビュー/指摘した記録」の ref_version は、下流（参照先ファイル）が版上げされるたびに RULE-004 ドリフトを出し続ける。これらを (a) 都度更新する／(b) 凍結スナップショットとしてドリフト免除する／(c) ドリフト＝「記録が陳腐化＝再検証が必要」のシグナルとして新記録の起票を促す、のいずれの意味論を採るか。

**選択肢**:
- **A**: 凍結記録は RULE-004 免除（VERIFY・resolved FND に suppress[RULE-004] を許容、または config でタイプ免除）。— ノイズ最小。ただし「いつの版を見たか」は本文に残す前提。
- **B**: 都度更新（記録も生きた依存辺として ref_version を最新化）。— 一貫するが、レビューしていない版を指す矛盾が生じうる。
- **C**: ドリフト＝再検証シグナルとして据え置き、陳腐化したら新 VERIFY/FND を起票（VERIFY-1 はそのまま、VERIFY-2 が現状を担う）。— 監査性は高いが恒常的にドリフト ERROR/WARNING が残る。

**推奨**: **A**（記録系は凍結し RULE-004 免除）。理由：VERIFY/解消済み FND は「過去の検証事実」であり、参照先の将来変更で書き換えるとレビュー証跡として不正確になる。免除しつつ「対象の版が変わったら再検証を検討」は運用ルール（PR2 機構＋デフォルト）で担保。C は恒常ノイズ、B は証跡の意味を壊す。

**影響範囲**: config に記録系タイプの RULE-004 免除機構を追加（設計段）。VERIFY-1・FND-2/4 等のドリフト解釈が確定。決定後は DD へ昇格。
