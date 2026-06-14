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
**推奨**: config の `must_link_to` の OR リストを `SPEC → [FR, NFR, SPEC]` に拡張し、子 SPEC（`-N` 採番）を機構として持つ。あるいは SPEC-14-1 に `to: FR-6` 直辺を付与する。**前者を推奨**（子 SPEC を今後も使うなら機構として持つべきで、SPEC-48 本文・接続マトリクスの意図と一致する）。本 PR が初めて子 SPEC（`-N` 採番）パターンを導入したが、config 側に `SPEC → SPEC` が用意されていなかった点が根因。
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
**推奨**: FND-24 と同根のため一括解消する。config を `SPEC → [FR, NFR, SPEC]` に拡張すれば、SPEC-48 本文（「SPEC の辺は FR・NFR・または別 SPEC を指す」）と config の機械判定が一致する。config を拡張せず SPEC-48 本文側を狭める選択肢もあるが、子 SPEC パターンを採用する方針なら config 拡張を推奨。
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
**推奨**: `docs/doc-system/03-connection-matrix.md` を DD-5 に合わせて §2/§3/§4 とも改訂する。具体的には (§2) must_link_to の mermaid を `SPEC --> FR` のみから `[FR, NFR]` 相当へ拡張・(§3) 被依存表に `NFR ← SPEC` を追加（現状 `NFR ← FND/TC/VERIFY` のみ）・(§4)「NFR は refines 上流にはならない（他要素が NFR を refines しない）」の記述を DD-5（`SPEC → NFR` 必須化）と整合する形に改訂。正本ドキュメント間（config と接続マトリクス）の矛盾を残したまま DD-5 を decided にするのは「矛盾は停止して打ち上げ」原則（PR）違反であり、マージ前解消が望ましい。
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
**推奨**: **(A) を推奨**。`trace_scope.exclude` に `**/00-dfd.md`（または `doc-system/**/00-dfd.md`）を追加して out-of-graph を正式化する。dashboard を `**/00-dashboard.md` で除外しているのと同じ機構であり、自称と config の食い違い（観測できない前提）を解消できる。
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
**補足**: dashboard の「ステージ別完成度」は requirements を「✅ N0 再点検済」と表示しているが、06-13 に追加された SPEC-44〜54・SPEC-14-1・FR-15/16 は VERIFY で再走査されておらず、実際 H1（FND-24）のような未検出違反が残っている。「✅点検済」表示が実態を上回っている。
**推奨**: 追加分を対象とした VERIFY を起票する（H1〜H3 解消後にまとめて再走査するのが望ましい）か、requirements 層のステータスを 🟡 に戻す。
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
**補足**（オーナー指摘の版ずれ実例・いずれも DD-2 の suppress[RULE-004] によるスナップショット設計だが監査時に DD→ファイルで版が合わず混乱を招く）: DD-2 影響範囲「doc-verify →0.1.2」が実 0.1.3（現 0.1.4）／DD-4 影響範囲「findings →0.1.4」が実 0.1.9（現 0.1.11）／DD-5・DD-6 影響範囲「spec 0.3.2」が実 0.3.4（現 0.3.5）。加えて VERIFY-3 が DD-2 の影響範囲に未記載。
**推奨**: DD の影響範囲注記が「決定時点のスナップショット」である旨を各 DD またはガイドに明示するか、監査用に「現在版」を併記する運用を検討。
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
**内容**: `doc-system/02-what/01-fr.md` 内の FR-1 ノードのバッジが `⬡ FR-1 · v0.3` だが、ファイルの frontmatter は `version: "0.2.5"`（x.y=0.2）。バッジの v0.3 はノード自体の改訂回数カウント、ファイル x.y はファイル全体の MAJOR.MINOR という別体系だが、ノードバッジと ref_version（ファイル x.y 基準）の対応関係が記法ガイドに明示されておらず、読者がバッジの意味を誤解する恐れがある。バッジが「ファイルの x.y」を示すと誤解した場合、ref_version: "0.2" との乖離（v0.3 vs 0.2）が誤りに見える。なお ref_version は `"0.2"` で RULE-004 上は正であり、誤読防止のためバッジ採番ルール（ノード改訂回数 vs ファイル x.y）の記法ガイド明記が望ましい。
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
**補足**: `tmp/doc-system/spec-41-49.md` の SPEC-41 は RULE-028 を「unknown field → WARNING」と定義しているが、最終 spec.md の RULE-028 は `labels`/`scheduled`/`edges` の欠如・型不正 → ERROR で**別物**であり、将来の誤参照源になる。tmp 草稿9本が最終版と重複してコミットされている。
**推奨**: tmp をコミットしない運用にする（`.gitignore` 追加など）か、撤去分（差し戻し済み SPEC-41/42/43 を含む草稿）を削除する。
**対応状況**: open
**指摘時 ref_version**: FND-18 "0.1"（doc-system/04-verification/02-findings.md v0.1.10 時点）

---
