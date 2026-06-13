---
version: "0.1.2"
---
# ドキュメント検証 — doc-system ドッグフーディング（要件〜分析層）

> **型**: VERIFY ／ **必須**: 対象要素への依存辺が1本以上（RULE-006 config: `must_link_to: VERIFY → any`）
> 無名依存辺のみ（`kind`/`status` なし・`to` は単数・全辺に `ref_version` 必須）。

---

## VERIFY-1: 要件〜分析層の spec-inspector レビュー

<details><summary>⬡ VERIFY-1 · v0.1</summary>

```yaml
id: VERIFY-1
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: VAL-1
    ref_version: "0.2"
  - to: FR-1
    ref_version: "0.2"
  - to: SPEC-1
    ref_version: "0.3"
  - to: ACTOR-1
    ref_version: "0.2"
  - to: I-1
    ref_version: "0.4"
  - to: P-1
    ref_version: "0.4"
  - to: E-1
    ref_version: "0.4"
  - to: DD-2
    ref_version: "0.1"
```
</details>

**検証手法**: spec-inspector（自動点検）＋メインスレッドによる裏取り。
**実施日**: 2026-06-11
**対象範囲**: doc-system/01-why〜03-analysis（VAL / SR / FR / NFR / SPEC / ACTOR / I / O / D / P / E）。各層の代表ノード（VAL-1・FR-1・SPEC-1・ACTOR-1・I-1・P-1・E-1）を検証アンカーとして紐づけた。
**結果**: 指摘あり（ERROR 1・WARNING 4・INFO 1）。

構造ルール群（ref_version ドリフト＝RULE-004、`kind`/`status` 残存、リスト記法の `to:`、存在しない ID 参照＝RULE-007、階層親不在）はいずれも新エッジモデルに準拠しており、致命的な構造破壊は検出されなかった。検出された指摘は系境界・粒度・網羅性・要件本文の記述ドリフトに関するもので、いずれも意味モデル上の論点である。

**発生した指摘**: → FND-1〜FND-6 を参照。

---

## VERIFY-2: N0（SPEC 品質強化分）再点検の実施記録

<details><summary>⬡ VERIFY-2 · v0.1</summary>

```yaml
id: VERIFY-2
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
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
  - to: DD-2
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
