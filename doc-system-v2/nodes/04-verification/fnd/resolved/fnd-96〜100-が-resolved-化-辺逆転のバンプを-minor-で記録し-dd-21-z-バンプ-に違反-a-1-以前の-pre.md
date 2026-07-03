**深刻度**: WARNING

**対応状況**: resolved（issue #40 の処置として本ブランチ `claude/issue-40-plan-0t1eqc` で起票＋適用是正・オーナー決定 2026-06-28）

**指摘時 ref_version**: FND-96 "0.5"／FND-97 "0.2"／FND-98 "0.2"／FND-99 "0.2"／FND-100 "0.2"（いずれも 02-findings.md の各 FND ノードバッジ x.y 時点＝是正前の現バッジ）。是正根拠（provenance）＝DD-21 "0.1"（resolved-FND の辺逆転/backref 付与を z＝PATCH バンプと確定・04-decisions.md）／DD-16 "0.1"（fnd_lifecycle 正式化・04-decisions.md）。これらは provenance のため辺は張らず本文記録のみ（DD-16 が FND-96 等へ辺を張らず本文記録した先例と同型）。

### 内容

resolved 済み FND **FND-96・FND-97・FND-98・FND-99・FND-100** が、lifecycle 辺逆転・`resolved: true` 化に伴うバージョンバンプを **MINOR（x.y を +1）で記録**しており、**DD-21（resolved-FND の辺逆転/backref 付与は z＝PATCH バンプと確定）に違反**している。

これは A-1（FND-101 辺逆転一括是正）が 75 件の resolved FND を MINOR バンプした結果 101 件の新規 backref ドリフトを生み、DD-21 でそれらを MINOR→z へ一括是正したのと**同一の原則違反**である。ただし FND-96〜100 は A-1 *以前* に lifecycle バンプ済み（pre-existing・改訂履歴混在）で、FND-101 は本コホートを「是正済みの手本」とみなし scope 外としていたため、A-1 の一括是正から漏れていた。DD-21 の残課題節（04-decisions.md L950）でも「FND-96/97/98/99/100 も A-1 以前に lifecycle 辺逆転で MINOR バンプ済みで同じ原則違反。pre-existing かつ改訂履歴が混在するため別途オーナー判断（FND 起票）とする」と明記されており、本 FND がその起票・是正にあたる。

**違反の本質**（DD-21 の確定原則を引用）: 辺逆転（forward 辺 `FND→対象` の削除＋`resolved: true` 化）と backref 付与（`対象→FND`）は、参照先の意味内容（FND の指摘事実）を変えず downstream の再レビューを要さない **provenance/lifecycle 操作** であり、DD-8 §4「backref 辺追加＝z バンプ」と同類である。よって x.y を据え置く z バンプが正しく、MINOR バンプは誤り。MINOR バンプすると FND バッジの x.y が動き、それを指す backref 辺（ref_version 据え置き）が `_drift()`（SPEC-9＝RULE-004）で一斉ドリフトと誤判定される。

### 違反の内訳と是正後バージョン（per-FND）

各 FND の改訂履歴を精査し、**純粋 lifecycle 遷移分（辺逆転＋resolved 化）を z へ訂正、正当な内容更新分は MINOR のまま温存**した。x.y は A-1 前＝本来の内容版へ戻し、z を +1 する（DD-21 影響範囲節の手順と同型）。

| FND | 是正前 | 是正後 | 該当の lifecycle 操作（z 化対象） |
|---|---|---|---|
| FND-96 | v0.5.0 | **v0.4.1** | v0.4→0.5「suppress 撤去＋resolved:true」＝純粋 lifecycle |
| FND-97 | v0.2.0 | **v0.1.1** | v0.1→0.2「suppress 撤去＋resolved:true」（1 回のみ）＝純粋 lifecycle |
| FND-98 | v0.2.0 | **v0.1.1** | v0.1→0.2「suppress 撤去＋resolved:true」（1 回のみ）＝純粋 lifecycle |
| FND-99 | v0.2.0 | **v0.1.1** | v0.1→0.2「forward 辺削除（辺逆転）＋記述明確化」＝主操作は辺逆転 |
| FND-100 | v0.2.0 | **v0.1.1** | v0.1→0.2「suppress 撤去＋resolved:true」（1 回のみ）＝純粋 lifecycle |

**FND-97 / FND-98 / FND-100**: 非初期バンプは「suppress 撤去＋`resolved: true` 追加」（DD-16 lifecycle 正式化に伴う 1 回のみ）であり、純粋な lifecycle 遷移＝z 相当。**v0.2.0 → v0.1.1**。これら 3 件の backref（ORC-1→FND-97／DD-13→FND-98／MOD-1・DM-3・DM-5・DM-6→FND-100）はすべて ref_version "0.1" のため、バッジを 0.1.x へ戻すだけで ref と x.y が一致しドリフトが解消する（**backref 改訂は不要**）。

**FND-99**: v0.1→v0.2 が「forward 辺削除（辺逆転）＋記述明確化」。主たる構造操作は辺逆転（z 相当・記述明確化は内容として独立 MINOR を要するほどの実体ではなく辺逆転に随伴する説明）であるため **v0.2.0 → v0.1.1**。FND-99 は out-of-graph 処置（7 著作資産への規則伝播）が対象で in-graph backref を持たない孤立ノード（意図的保持・FND-101 系の孤立シグナル）であり、backref ドリフトの懸念はない。

**FND-96（混在の本丸）**: 改訂履歴が正当な内容 MINOR と lifecycle 操作で混在する。
- v0.1→v0.2: 内容拡充＝**正当な内容 MINOR（温存）**
- v0.2→v0.3: 選択肢A 確定＝**正当な内容 MINOR（温存）**
- v0.3→v0.4: resolved 記録（実質的な対応内容＝処置成果の記述）＋辺逆転の混在。対応内容という実体ある記述を含むため最後の正当内容版とみなす＝**v0.4 を最終内容版（温存）**
- v0.4→v0.5: 「suppress 撤去＋`resolved: true`」＝**純粋 lifecycle → z へ訂正**

よって最後の正当内容版を v0.4 とみなし、純粋 lifecycle 分（v0.4→0.5）を z へ畳んで **v0.5.0 → v0.4.1**。

### backref ドリフトの現状と解消

resolved FND の MINOR バンプは、それを指す backref 辺（処置対象 X→FND・ref_version 据え置き）と FND バッジの x.y を食い違わせ、`_drift()`（SPEC-9 v0.2.1＝RULE-004）が一斉ドリフトと誤判定する。本コホートが現に生んでいる誤検知ノイズは以下のとおり（起票時に Read で確認）。

| backref 辺 | 現 ref | 現バッジ | 是正後バッジ | 解消手段 |
|---|---|---|---|---|
| ORC-1 → FND-97 | "0.1" | 0.2 | 0.1 | バッジ戻しで ref 一致・改訂不要 |
| DD-13 → FND-98 | "0.1" | 0.2 | 0.1 | バッジ戻しで ref 一致・改訂不要 |
| MOD-1 → FND-100 | "0.1" | 0.2 | 0.1 | バッジ戻しで ref 一致・改訂不要 |
| DM-3 → FND-100 | "0.1" | 0.2 | 0.1 | バッジ戻しで ref 一致・改訂不要 |
| DM-5 → FND-100 | "0.1" | 0.2 | 0.1 | バッジ戻しで ref 一致・改訂不要 |
| DM-6 → FND-100 | "0.1" | 0.2 | 0.1 | バッジ戻しで ref 一致・改訂不要 |
| MOD-1 → FND-96 | "0.3" | 0.5 | 0.4 | **ref を "0.3"→"0.4" へ訂正**（後述） |
| Q-4 → FND-96 | "0.4" | 0.5 | 0.4 | バッジ戻しで ref 一致・改訂不要 |

FND-97/98/100 を指す backref はすべて ref "0.1" で揃っており、バッジを 0.1.x へ戻すだけで x.y が一致しドリフトが解消する（backref 改訂は一切不要）。

**FND-96 の不揃い解消（最も裁量が要る点）**: FND-96 は **2 本の backref が不揃い**（MOD-1→FND-96 ref "0.3"／Q-4→FND-96 ref "0.4"）であり、現バッジ 0.5 と両方ドリフトしている。是正後バッジは 0.4（最終内容版＝対応内容を記録した版）であるため、**MOD-1→FND-96 の ref を "0.3"→"0.4" へ訂正**する。根拠は、FND-96 への指摘確定・処置成果が記録された正本バージョンが v0.4 であり、処置対象 MOD-1 はその確定済み指摘を参照すべきだからである（v0.3 時点はまだ選択肢A 確定前で、MOD-1 の処置が依拠した版ではない）。これにより MOD-1・Q-4 とも ref "0.4" で揃い、是正後バッジ 0.4 とドリフトが解消する。DD-21 が 5 件の backref ref（D-18/P-7-2/FR-5/FR-1/DM-1）を z バンプ整合のため訂正した先例に倣う（実体のない更新ではなく、指摘確定版への整合訂正）。

### 被参照確保（MOD-1 アンカー・RULE-005 非発火）

本 FND は単一の in-graph 処置対象を持たないバッチ FND（resolved-FND コホートの版バンプ是正）であり、FND-101 と同型である。被参照のアンカー選定には config の resolved-FND ルールを尊重する必要がある——**処置対象 FND-96〜100 はいずれも resolved FND** であり、config の `fnd_lifecycle.resolved.must_not_link_to: { target: any, severity: warning }`「resolved FND の元 forward 辺は削除済みであること」により、resolved FND が `to:` 辺（forward）を 1 本でも持つと warning が発火する。frontmatter の `FND-96 → FND-110` 等は **forward 辺**としてカウントされるため、5 件の resolved FND に backref を張ると新規 warning を 5 件生む。よって **処置対象 FND からの被参照は採れない**（FND-101 が処置対象全 resolved のため backref を諦め、非 resolved の Q-5 で非孤立を確保したのと同じ制約）。

**アンカーは MOD-1 とする**。MOD-1 は本是正で `→FND-96` の ref を "0.3"→"0.4" に訂正される **非 resolved の in-graph 処置対象**（設計層ノード）であり、forward 辺に制約がない。`MOD-1 → FND-110`（ref_version "0.1"・forward 辺）を付与すれば、FND-110 の `must_be_linked_from`（resolved FND は処置対象からの backward 辺必須・severity error の孤立）を満たせる。これは「処置対象（MOD-1）→ FND」の標準 backref パターンそのものであり、FND-101 が Q-5 の参照で非孤立を確保したのと同じ目的を、本件は MOD-1 backref で達成する。

- **FND-110 自身の `edges` は `[]`**（resolved FND は `must_not_link_to` により forward 辺を持てない）。
- **incoming は MOD-1 → FND-110 の 1 本**（ref_version "0.1"＝本 FND-110 のバッジ x.y）。

これにより FND-110 は incoming 1 本を持ち、`must_be_linked_from`（severity error の孤立）を満たし RULE-005（完全孤立）も発火しない。`suppress` は不要（孤立エラー自体が発生しない）。

> **FND-96〜100 には `→FND-110` を付与しない**（resolved のまま `edges: []` を維持）。各々は既存の incoming（MOD-1/ORC-1/DD-13/Q-4/DM 群）で `must_be_linked_from` を充足済みであり、本 FND-110 の被参照のために新たな forward 辺を負わせると逆に `must_not_link_to` warning を 5 件生む。FND-99 は従来どおり意図的孤立（out-of-graph 処置・FND-101 系の孤立シグナル）を保持する。

### 深刻度判定の根拠

**WARNING**。MINOR バンプ自体は機械 RULE 違反ではないため **live な機械 RULE 失敗は発生していない**。しかし backref 辺の ref_version と FND バッジ x.y の食い違いにより `_drift()`（SPEC-9＝RULE-004）が誤検知ノイズを出し、DD-21 が確定した z バンプ原則に構造的に違反する負債である（resolved-FND の辺逆転/backref は downstream 無影響の provenance/lifecycle 操作であり z が正・MINOR は誤適用）。live RULE 失敗を伴わない構造的ドリフトは WARNING とする FND-101 の判定基準に倣う。

### 是正方針（DD-21 適用徹底・選択肢A）

DD-21 は drift ルール（SPEC-9＝RULE-004）も DD-8 も変更せず、既存 DD-8 §4「backref 辺追加＝z バンプ」の適用を徹底するのみと確定した。本 FND はその原則を A-1 漏れコホート（FND-96〜100）に適用する：

1. 各 FND のバッジ・本文版表記を z バンプへ訂正（x.y を最終内容版へ戻し z を +1）：FND-96 v0.5.0→**v0.4.1**／FND-97・98・99・100 v0.2.0→**v0.1.1**。各 FND の改訂理由の版種別を「MINOR」→「z」相当へ訂正し、本 FND-110/DD-21 を provenance として参照する旨を本文に追記する。
2. FND-96 の backref 不揃いを解消：**MOD-1→FND-96 の ref "0.3"→"0.4"**（指摘確定版への整合訂正）。他の backref（Q-4→FND-96 ref "0.4"／FND-97/98/100 系 ref "0.1"）はバッジ戻しで自動的に整合し改訂不要。
3. 非 resolved の処置対象 **MOD-1 に `→FND-110`（ref "0.1"）forward 辺を付与**（本 FND の非孤立化）。処置対象 FND-96〜100 は resolved のため backref を負わせず `edges: []` を維持（`must_not_link_to` warning 回避）。

### 対応内容（issue #40・本ブランチ是正）

- **5 FND の z バンプ再訂正**: FND-96 v0.5.0→v0.4.1／FND-97・98・99・100 v0.2.0→v0.1.1。各 FND のバッジ（`<details>` summary）・本文の版表記・改訂理由の版種別を z へ訂正（reconciliation が 02-findings.md へ反映）。
- **MOD-1→FND-96 backref ref 訂正**: "0.3"→"0.4"（`doc-system/05-design/01-modules.md`・是正後バッジ 0.4 へ整合・MOD-1・Q-4 とも ref "0.4" で揃う）。他 backref（ORC-1→FND-97／DD-13→FND-98／MOD-1・DM-3・DM-5・DM-6→FND-100／Q-4→FND-96）は ref 据え置きでバッジ戻しにより自動整合（改訂不要）。
- **被参照確保（MOD-1 アンカー）**: 非 resolved の処置対象 **MOD-1 に `→FND-110`（ref "0.1"・forward 辺）を付与**（`doc-system/05-design/01-modules.md`）。FND-110 の `must_be_linked_from`（severity error の孤立）を 1 本の incoming で充足。**FND-96〜100 には `→FND-110` を付与しない**（resolved のまま `edges: []` 維持・既存 incoming で充足済み・付与すると `must_not_link_to` warning を生むため）。FND-110 自身は `edges: []`。
- **provenance 記録のみ**: DD-21・DD-16 への backref/forward 辺は張らず本文記録のみ（resolved FND は forward 不可・DD は forward 対象外＝DD-16/DD-21 先例）。

### 主な変更ファイル

- `doc-system/04-verification/02-findings.md`: FND-110 新設。FND-96 v0.5.0→v0.4.1／FND-97・98・99・100 v0.2.0→v0.1.1 の z バンプ再訂正（バッジ・本文版表記・改訂理由の版種別）。
- `doc-system/05-design/01-modules.md`: **MOD-1 に `→FND-110`（ref "0.1"）forward 辺を追加**（FND-110 の被参照アンカー）。併せて既存 `MOD-1 → FND-96` の ref を "0.3"→"0.4" へ訂正。

### 接続規則変更チェック（FND-99 パターン）

本 FND は **resolved-FND の版バンプ種別（MINOR→z）の運用適用を是正するのみ**で、`config.yaml` の接続規則・`fnd_lifecycle`・`decision_spine`・SPEC-9（RULE-004）・DD-8 のいずれも追加・変更・削除しない（DD-21 が選択肢D＝ルール改変を却下し、既存ルールの適用是正に留めたのと同じ）。よって接続マトリクス（03-connection-matrix.md）・ドキュメント一覧（01-document-items.md）・各 author エージェント／スキルへの規則伝播は不要（DD-21 の同チェックと同一判定）。版バンプ種別は DD-8 で既に定義済みのため DD-8 本体への規則追記も不要。
