# ドキュメント検証 — doc-system ドッグフーディング（要件〜分析層）

> **型**: VERIFY ／ **必須**: 対象要素への依存辺が1本以上（RULE-006 config: `must_link_to: VERIFY → any`）
> 無名依存辺のみ（`kind`/`status` なし・`to` は単数・全辺に `ref_version` 必須）。

---

## VERIFY-1: 要件〜分析層の spec-inspector レビュー

<details><summary>⬡ VERIFY-1 · v0.1.0</summary>

```yaml
id: VERIFY-1
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: VAL-1
    ref_version: "0.2.0"
  - to: FR-1
    ref_version: "0.2.0"
  - to: SPEC-1
    ref_version: "0.3.0"
  - to: ACTOR-1
    ref_version: "0.2.0"
  - to: I-1
    ref_version: "0.4.0"
  - to: P-1
    ref_version: "0.4.0"
  - to: E-1
    ref_version: "0.4.0"
  - to: DD-2
    ref_version: "0.1.0"
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

<details><summary>⬡ VERIFY-2 · v0.1.0</summary>

```yaml
id: VERIFY-2
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: FR-11
    ref_version: "0.2.0"
  - to: FR-13
    ref_version: "0.2.0"
  - to: FR-14
    ref_version: "0.2.0"
  - to: SPEC-31
    ref_version: "0.3.0"
  - to: SPEC-40
    ref_version: "0.3.0"
  - to: FND-16
    ref_version: "0.1.0"
  - to: FND-17
    ref_version: "0.1.0"
  - to: Q-1
    ref_version: "0.1.0"
  - to: DD-2
    ref_version: "0.1.0"
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

## VERIFY-3: N5（P 単一責務点検）の実施記録

<details><summary>⬡ VERIFY-3 · v0.1.0</summary>

```yaml
id: VERIFY-3
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: P-1
    ref_version: "0.6.0"
  - to: P-4
    ref_version: "0.6.0"
  - to: P-5
    ref_version: "0.6.0"
  - to: P-6
    ref_version: "0.6.0"
  - to: P-7
    ref_version: "0.6.0"
  - to: DD-2
    ref_version: "0.1.0"
```
</details>

**検証手法**: メインスレッドによる P ノードの単一責務点検（DFD レベリング規律 PR9・本文責務記述と対応 SPEC の突合）。
**実施日**: 2026-06-13
**対象範囲**: processes.md v0.6.3 の P-1（受付・パース）・P-4（レポート生成）・P-5（設定ファイル読み込み）・P-6（in-graph 集合決定）・P-7（ノード著作プロセス）。P-2/P-3 は FND-2/FND-4 で既に分解済みのため本回の対象外。

**各 P の判定**:
- **P-1「受付・パース」**: パース段検証（RULE-023〜028）の責務が本文の責務記述に含まれず、対応 SPEC（SPEC-2/32/33/34/35/36/52/53）がどの P からも参照されない無主状態 → 価値経路の上流欠落（PR6）→ **FND-20**。
- **P-4「レポート生成」**: 整列・整形・出力・終了コードは出力側の単一データフローを成し、責務分割の必要なし → **単一責務 PASS**。
- **P-5「設定ファイル読み込み」**: config 取り込みの単一責務 → **PASS**。
- **P-6「in-graph 集合決定」**: trace_scope 照合による in-graph 集合決定の単一責務 → **PASS**。
- **P-7「ノード著作プロセス」**: (1) 著作（agent→tmp）と (2) 調停（reconciliation→本ファイル）の2活動を1プロセスに内包し、別アクタ・別段階のため単一責務違反（PR9）→ **FND-19**。

**結果**: 指摘 2 件（WARNING 2＝FND-19・FND-20）。P-4/P-5/P-6 は単一責務 PASS。

**発生した指摘**: → FND-19・FND-20 を参照。

---

## VERIFY-4: PR #21 オーナーレビュー点検記録

<details><summary>⬡ VERIFY-4 · v0.1.0</summary>

```yaml
id: VERIFY-4
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: SPEC-14-1
    ref_version: "0.3.0"
  - to: SPEC-48
    ref_version: "0.3.0"
  - to: FR-15
    ref_version: "0.2.0"
  - to: FR-16
    ref_version: "0.2.0"
  - to: DD-7
    ref_version: "0.1.0"
  - to: FND-24
    ref_version: "0.1.0"
  - to: FND-25
    ref_version: "0.1.0"
  - to: FND-26
    ref_version: "0.1.0"
  - to: FND-27
    ref_version: "0.1.0"
  - to: FND-28
    ref_version: "0.1.0"
  - to: FND-29
    ref_version: "0.1.0"
  - to: FND-30
    ref_version: "0.1.0"
  - to: FND-31
    ref_version: "0.1.0"
  - to: FND-32
    ref_version: "0.1.0"
  - to: FND-33
    ref_version: "0.1.0"
  - to: DD-2
    ref_version: "0.1.0"
```
</details>

**検証手法**: オーナーレビュー（PR #21 review）
**実施日**: 2026-06-13
**対象範囲**: PR #21（claude/doc-system-sprint2）の追加分全体。SPEC-14-1（RULE-006 検査）・SPEC-48（USDM 制約・config 整合）・FR-15/16（依存グラフ機能）・分析層（DFD・D-3〜D-8・I-9）・DD-7・trace_scope 設定
**結果**: ERROR 3件（H1/H2/H3）・WARNING 4件（M1/M2/M3/M4）・INFO 3件（L1/L2/L3）。計10件 → FND-24〜FND-33
**発生した指摘**: → FND-24〜FND-33 を参照

---

## VERIFY-5: requirements 層追加バッチ再点検記録（FND-28 処置）

<details><summary>⬡ VERIFY-5 · v0.1.0</summary>

```yaml
id: VERIFY-5
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: SPEC-44
    ref_version: "0.3.0"
  - to: SPEC-14-1
    ref_version: "0.3.0"
  - to: FR-15
    ref_version: "0.2.0"
  - to: SPEC-54
    ref_version: "0.3.0"
  - to: DD-5
    ref_version: "0.1.0"
  - to: FND-28
    ref_version: "0.1.0"
  - to: FND-34
    ref_version: "0.1.0"
```
</details>

**検証手法**: 手動点検（H1〜H3 処置後・2026-06-14）
**実施日**: 2026-06-14
**対象範囲**: 2026-06-13 以降に追加された requirements 層ノード（SPEC-44〜54・SPEC-14-1・FR-15/16）。具体的には以下の由来バッチを対象とした。

- **DD-5 由来**: SPEC-44〜49（NFR-1〜6 各1件・condition: normal）← spec.md
- **DD-6 由来**: FR-15/16（依存グラフ・複雑度算出）← fr.md、SPEC-50/51（FR-15/16 の SPEC 子）← spec.md
- **FND-18/23 由来**: SPEC-14-1（FR-6 child SPEC）、SPEC-54（FR-13 P-7 入力）← spec.md
- **修正後確認**: H1 処置（FND-24・2026-06-14）で config `SPEC→[FR, NFR, SPEC]` 拡張済み

**結果**: PASS（指摘なし）

**点検項目**:

1. **FR-15/16 の必須接続**: FR-15/16 → SR-2 辺あり ✓、SPEC 子（SPEC-50/51）あり ✓
2. **SPEC-44〜49 の必須接続**: SPEC-44〜49 → NFR-1〜6 辺あり ✓、全ノードに `condition: normal` ✓
3. **SPEC-50/51 の必須接続**: SPEC-50/51 → FR-15/16 辺あり ✓、`condition: normal` ✓
4. **SPEC-14-1 の必須接続**: SPEC-14-1 → SPEC-14 辺あり ✓（H1 処置後 config `SPEC→[FR, NFR, SPEC]` により RULE-006 解消）
5. **SPEC-54 の必須接続**: SPEC-54 → FR-13 辺あり ✓、`condition: normal` ✓
6. **孤立ノードなし（RULE-005）**: バッチ全体で完全孤立（in/out 辺ゼロ）ノードなし ✓
7. **存在しない ID 参照なし（RULE-007）**: 全辺の `to` が実在するノード ID ✓
8. **condition 属性の完備（RULE-016）**: バッチ内の全 SPEC ノードに `condition` 属性あり ✓

**所見**: FND-24（SPEC-14-1 の RULE-006 違反）は当初 VERIFY から漏れていたが H1 処置で config 拡張が完了し SPEC-14-1→SPEC-14 辺が有効な依存辺として承認された。バッチ全体は現時点で構造ルールに適合している。

**発生した指摘**: なし（PASS）
