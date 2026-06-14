---
# PR #21 レビュー指摘 — VERIFY-4 および FND-24〜33
# 出力先: tmp/doc-system/verify4-fnd24-33.md
# 著作: verification-author
# 対象: PR #21（branch: claude/doc-system-sprint2）オーナーレビュー指摘
---

## VERIFY-4: PR #21 オーナーレビュー点検記録

<details><summary>⬡ VERIFY-4 · v0.1</summary>

```yaml
id: VERIFY-4
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: SPEC-14-1
    ref_version: "0.3"
  - to: SPEC-48
    ref_version: "0.3"
  - to: FR-15
    ref_version: "0.2"
  - to: FR-16
    ref_version: "0.2"
  - to: DD-7
    ref_version: "0.1"
  - to: FND-24
    ref_version: "0.1"
  - to: FND-25
    ref_version: "0.1"
  - to: FND-26
    ref_version: "0.1"
  - to: FND-27
    ref_version: "0.1"
  - to: FND-28
    ref_version: "0.1"
  - to: FND-29
    ref_version: "0.1"
  - to: FND-30
    ref_version: "0.1"
  - to: FND-31
    ref_version: "0.1"
  - to: FND-32
    ref_version: "0.1"
  - to: FND-33
    ref_version: "0.1"
  - to: DD-2
    ref_version: "0.1"
```
</details>

**検証手法**: オーナーレビュー（PR #21 review）
**実施日**: 2026-06-13
**対象範囲**: PR #21（claude/doc-system-sprint2）の追加分全体。SPEC-14-1（RULE-006 検査）・SPEC-48（USDM 制約・config 整合）・FR-15/16（依存グラフ機能）・分析層（DFD・D-3〜D-8・I-9）・DD-7・trace_scope 設定
**結果**: ERROR 3件（H1/H2/H3）・WARNING 4件（M1/M2/M3/M4）・INFO 3件（L1/L2/L3）。計10件 → FND-24〜FND-33
**発生した指摘**: → FND-24〜FND-33 を参照

---

## FND-24: H1: SPEC-14-1 RULE-006 違反（FR/NFR への直接辺なし）

<details><summary>⬡ FND-24 · v0.1</summary>

```yaml
id: FND-24
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-14-1
    ref_version: "0.3"
```
</details>

**深刻度**: ERROR
**内容**: SPEC-14-1（カバレッジテーブルの出力フォーマット・normal）の edges が `to: SPEC-14`（親 SPEC）と `to: FND-18` のみであり、FR または NFR への直接辺が存在しない。config.yaml の `must_link_to: SPEC → [FR, NFR]`（RULE-006・severity: error）違反。SPEC-14-1 は SPEC-14 の -N 分割ノードだが、config の必須接続は FR/NFR への直辺を要求しており、SPEC→SPEC のみでは RULE-006 を満たさない。
**対応状況**: open
**指摘時 ref_version**: SPEC-14-1 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）

---

## FND-25: M1: SPEC-48 本文が SPEC→SPEC を有効と明記するが config はそれを強制しない矛盾

<details><summary>⬡ FND-25 · v0.1</summary>

```yaml
id: FND-25
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: SPEC-48
    ref_version: "0.3"
```
</details>

**深刻度**: WARNING
**内容**: SPEC-48（各ノードは直接の親のみへ辺を張る・USDM 1段制約）の本文に「接続マトリクスで SPEC の直接親は FR または別 SPEC と定義されている」「SPEC の `edges[].to` が FR・NFR・または別 SPEC（直接親 SPEC）を指す」と明記されている。一方 config.yaml の `must_link_to: SPEC → [FR, NFR]` には SPEC→SPEC は含まれておらず、機械検査上は SPEC→SPEC のみのノードが RULE-006 ERROR になる。FND-24（SPEC-14-1）の違反はこの不整合が根因。SPEC-48 本文か config の `must_link_to` のいずれかを修正する必要がある。
**対応状況**: open
**指摘時 ref_version**: SPEC-48 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）

---

## FND-26: H2: docs/doc-system/03-connection-matrix.md が DD-5 と未同期で矛盾

<details><summary>⬡ FND-26 · v0.1</summary>

```yaml
id: FND-26
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-5
    ref_version: "0.1"
```
</details>

**深刻度**: ERROR
**内容**: DD-5（NFR から SPEC 導出を必須化・2026-06-13 反映完了）により config.yaml が `must_link_to: SPEC → [FR, NFR]` に更新され `must_be_linked_from: NFR ← [SPEC]` が追加されたが、`docs/doc-system/03-connection-matrix.md`（v0.2.0）は更新されていない。具体的な不整合：§2 接続要否マトリクス表の SPEC 行が FR のみ必須（NFR なし）・§4「NFR は `refines` 上流にはならない（他要素が NFR を refines しない）」が DD-5 の「SPEC→NFR を必須化」と直接矛盾。接続マトリクスは「人が読める全体像」として正本 config.yaml と一致すべきだが、DD-5 適用後に同期されていない。
**対応状況**: open
**指摘時 ref_version**: DD-5 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-27: H3: doc-system/03-analysis/00-dfd.md が out-of-graph 自称するが trace_scope.exclude に未登録

<details><summary>⬡ FND-27 · v0.1</summary>

```yaml
id: FND-27
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-7
    ref_version: "0.1"
```
</details>

**深刻度**: ERROR
**内容**: `doc-system/03-analysis/00-dfd.md`（v0.2.2）の本文に「本ファイルは派生図（ノードを持たない）」と記載され out-of-graph を自称するが、config.yaml の `trace_scope.include: ["doc-system/**/*.md"]` に含まれ、`trace_scope.exclude` には未登録。spec-inspector はこのファイルを走査しノードを抽出しようとするが、ファイル内には `<details>` YAML ブロックのノードが存在しないため「in-graph ファイルだがノードゼロ」という矛盾状態になる。修正方針：(A) `trace_scope.exclude` に `"**/00-dfd.md"` を追加して out-of-graph を正式化 か (B) out-of-graph 自称を削除しノードを持たない in-graph ファイルとして運用。
**対応状況**: open
**指摘時 ref_version**: DD-7 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-28: M2: SPEC-44〜54/SPEC-14-1/FR-15/16 追加バッチを対象とした VERIFY が存在しない

<details><summary>⬡ FND-28 · v0.1</summary>

```yaml
id: FND-28
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FR-15
    ref_version: "0.2"
  - to: SPEC-54
    ref_version: "0.3"
```
</details>

**深刻度**: WARNING
**内容**: VERIFY-1（2026-06-11）・VERIFY-2（2026-06-12 N0 再点検）・VERIFY-3（2026-06-13 P 単一責務）は、それぞれの対象範囲以降に追加された SPEC-44〜54・SPEC-14-1・FR-15/16 を含まない。これらの追加バッチ（NFR→SPEC 導出強化・依存グラフ機能・SPEC-14-1 など）について spec-inspector による参照整合・カバレッジ・RULE 検査の記録がなく、FND-24（SPEC-14-1 RULE-006 違反）が VERIFY から漏れた事実も VERIFY 空白を示す。追加バッチ全体を対象とした VERIFY を起票する必要がある。
**対応状況**: open
**指摘時 ref_version**: FR-15 "0.2"（doc-system/02-what/01-fr.md v0.2.5 時点）、SPEC-54 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）

---

## FND-29: M3: PR #21 説明文が実変更と大きく乖離

<details><summary>⬡ FND-29 · v0.1</summary>

```yaml
id: FND-29
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: P-7-2
    ref_version: "0.6"
```
</details>

**深刻度**: WARNING
**内容**: PR #21 の説明文は VERIFY-2（N0 再点検）・FND-16/17 副次発見・Q-1 起票のみを記述しているが、実際の PR は16コミット・31ファイル変更を含む大幅な追加があり、説明と実態が乖離している。実際の内容（VERIFY-3・DD-2〜7・SPEC-44〜54・SPEC-14-1・FR-15/16・D-3〜D-8・I-9・P-7→P-7-1/P-7-2・DFD Level 0/1/2・config.yaml 更新・エージェント更新・PEND-2・FND-18〜23 解消）が PR 説明に反映されていない。調停プロセス（P-7-2）が生成した成果物（O-3・著作済みノードファイル群）と PR 説明の間に整合が取れていない状態。
**対応状況**: resolved（PR #21 本文を最新状態に更新済み）
**バックリファレンス辺**: PR #21 description は GitHub 上の out-of-graph 成果物であり in-graph ノードではないため、`→FND-29` バックリファレンス辺の付与先ノードが存在しない。
**指摘時 ref_version**: P-7-2 "0.6"（doc-system/03-analysis/03-processes.md v0.6.6 時点）

---

## FND-30: M4: ダッシュボード「判断待ち 計 0 件」と N1 記載の自己矛盾

<details><summary>⬡ FND-30 · v0.1</summary>

```yaml
id: FND-30
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-7
    ref_version: "0.1"
```
</details>

**深刻度**: WARNING
**内容**: doc-system/00-dashboard.md の「オーナー判断待ち（サマリ）」セクションに「計 0 件」と記載されているが、同じダッシュボードの「推奨ネクストアクション」テーブルには N1「current_stage を analysis へ進める判断・🟡 中」が「判断待ち」として掲載されており自己矛盾。N1 はオーナーが判断すべき未決項目であり「計 1 件」が正しい。
**対応状況**: resolved（ダッシュボードの「計 0 件」→「計 1 件」に修正し、N1 を判断待ちテーブルに追加済み）
**バックリファレンス辺**: 00-dashboard.md は `trace_scope.exclude` に登録された out-of-graph ファイル（ノードを持たない）であり in-graph ノードではないため、`→FND-30` バックリファレンス辺の付与先ノードが存在しない。
**指摘時 ref_version**: DD-7 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-31: L1: DD 影響範囲のバージョン注記が現在の frontmatter と乖離

<details><summary>⬡ FND-31 · v0.1</summary>

```yaml
id: FND-31
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-5
    ref_version: "0.1"
```
</details>

**深刻度**: INFO
**内容**: 各 DD の「影響範囲」に記載されたファイルのバージョン注記（例：`doc-system/02-what/03-spec.md`（v0.3.0→0.3.1）等）は、DD 決定時点のバージョン遷移を記録したものだが、その後の追加変更でファイルは更に版上げされており、影響範囲に書かれたバージョンが「当時の変更前後」であって「現在の最終版」を示さないことが不明瞭。読者が DD の影響範囲と現在のファイル版を照合しようとすると乖離が見つかる（例：DD-5 影響範囲では spec.md が v0.3.0→0.3.1 と記載されているが現在は v0.3.5）。DD は決定時点のスナップショットとして書かれているが（DD-2 により suppress[RULE-004] がある）、注記の意図が明示されていないため混乱を招く可能性がある。
**対応状況**: open
**指摘時 ref_version**: DD-5 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）

---

## FND-32: L2: FR-1 ノードバッジ v0.3 と fr.md ファイル version x.y=0.2 の不一致

<details><summary>⬡ FND-32 · v0.1</summary>

```yaml
id: FND-32
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FR-1
    ref_version: "0.2"
```
</details>

**深刻度**: INFO
**内容**: `doc-system/02-what/01-fr.md` 内の FR-1 ノードのバッジが `⬡ FR-1 · v0.3` だが、ファイルの frontmatter は `version: "0.2.5"`（x.y=0.2）。バッジの v0.3 はノード自体の改訂回数カウント、ファイル x.y はファイル全体の MAJOR.MINOR という別体系だが、ノードバッジと ref_version（ファイル x.y 基準）の対応関係が記法ガイドに明示されておらず、読者がバッジの意味を誤解する恐れがある。バッジが「ファイルの x.y」を示すと誤解した場合、ref_version: "0.2" との乖離（v0.3 vs 0.2）が誤りに見える。
**対応状況**: open
**指摘時 ref_version**: FR-1 "0.2"（doc-system/02-what/01-fr.md v0.2.5 時点）

---

## FND-33: L3: tmp 草稿に差し戻し済み SPEC-41〜43 と旧 RULE-028 定義が残存

<details><summary>⬡ FND-33 · v0.1</summary>

```yaml
id: FND-33
type: FND
labels: []
scheduled: ""
suppress: []
edges:
  - to: FND-18
    ref_version: "0.1"
```
</details>

**深刻度**: INFO
**内容**: `tmp/doc-system/spec-41-49.md` に FND-18 初回処置で差し戻し済みの SPEC-41（I-1 完全スキーマ）・SPEC-42（O-2 カバレッジ出力）・SPEC-43（I-7 テンプレート構造）の草稿が残存し、最終 spec.md（v0.3.5）の RULE-028 定義とは異なるバージョンの RULE-028 記述が含まれる。`tmp/doc-system/fnd18-redo.md` にも旧 RULE-028 定義が含まれる。tmp は working draft であり主ファイルとは独立するが、同一 SPEC ID の別定義が検索時に混乱を生む恐れがある。また tmp/doc-system/n5-verify-fnd.md にも RULE-028 への参照がある。
**対応状況**: open
**指摘時 ref_version**: FND-18 "0.1"（doc-system/04-verification/02-findings.md v0.1.10 時点）
