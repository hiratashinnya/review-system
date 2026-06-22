# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> **状態と優先度の要約**に絞る——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は要約のみ。**全件列挙はしない**。
>
> **最終更新**: 2026-06-22 ｜ **current_stage**: `design`（`docs/doc-system/config.yaml`）
> 直近: **issue #30 PR #34 レビュー対応（origin/main マージ後の config 整合）**（2026-06-22）。ブランチが古い config（FND→any が must_link_to 内・計45行）基準だったため、main の Q-4→DD-16（FND→any を fnd_lifecycle へ移管・標準44行）を取り込み、FND-102 の計数を 45行/既存9 → **44行/既存8** へ訂正。SPEC-18-1 を `fnd_lifecycle.unresolved.must_link_to` 参照へ付替え。fnd_lifecycle 残2ルール（resolved.must_be_linked_from／must_not_link_to）の dedicated 化は **FND-103**（INFO・open）で別途追跡。直近の **Q-4 → DD-16 昇格・選択肢A 採用**（FND 専用ライフサイクルルールを config に独立定義・2026-06-21）。設計層は MOD-1〜18 / PORT-1 / DS-1〜3 / PRS-1 / ORC-1〜2 / DM-1〜6 の計 31 ノード＋TERM-1〜6。

---

## 🔄 直近の作業

| 作業 | 種別 | 状態 |
|---|---|---|
| FND-103 処置（案②・責務分離）— fnd_lifecycle resolved 系2ルールの dedicated SPEC 化 | FND-103 | 🔄 部分処置（2026-06-22）。`must_be_linked_from`（辺欠如/error）→ **SPEC-18-9 反映済み**（SPEC-18 傘の子・RULE-006 ERROR）。`must_not_link_to`（辺残留/warning）→ SPEC-59 著作したが **保留**：config の同ルールを検出する RULE が 05-verification.md に未定義と判明し **FND-104（WARNING）起票**。SPEC-59 は RULE 決定後に確定。配置はオーナー決定で責務分離（辺欠如=SPEC-18 傘／辺残留=SPEC-12/55 系統の独立 SPEC） |
| issue #30 必須辺の仕様化漏れ点検 — 必須辺 config 44 行の SPEC 被覆点検＋全 dedicated SPEC 化（worktree） | FND-102 | ✅ resolved（2026-06-21）。点検結論＝完全起票漏れ無し（SPEC-8 が parametric に全行被覆）だが dedicated SPEC は 8/44 のみ。FND-102 起票→オーナー決定②で **SPEC-56/57/58 傘＋36 子・SPEC-18-6〜8・SPEC-28-3 を新設**し 44 行全 dedicated 化（行→SPEC 1:1）。新設傘に `→FND-102` backref。索引表は FND-79 領分。FND→any は fnd_lifecycle へ移動・残課題は FND-103 で追跡 |
| DM-3 v0.3（PR #32 再レビュー 🟡 対応・D-7 穴リスト部分を実現する D に追記） | DM-3 | ✅ done（2026-06-21）。DM-5 本文が「D-7 穴リスト部分は DM-3 が担う」と明記する一方 DM-3 の「実現する D」に D-7 未記載だった prose 非対称を是正。推奨案 (a)（D-7 追記で対称化）。構造変更・edges 変更なし（D-7 の MOD-1 realize 辺は既存） |
| FND ライフサイクル「辺の逆転」正式化 — Q-4 → DD-16 昇格・FND-96/97/98/100 suppress 撤去 | DD-16 / Q-4 closed / FND ×4 | ✅ 処置完了（2026-06-21）。Q-4 選択肢A 採用（DD-16）。config.yaml に `fnd_lifecycle` 専用セクション新設（resolved_field/unresolved.must_link_to/resolved.must_be_linked_from/resolved.must_not_link_to）・汎用 RULE-006 FND 行を削除。FND-96（v0.5）/97（v0.2）/98（v0.2）/100（v0.2）の `suppress: [RULE-006]` 撤去・`resolved: true` 追加。接続マトリクス・文書一覧・verification-author 著作資産へも同期。FND-101 別ブランチ |
| PR #32 レビュー対応 — FND-96 処置後の DM↔MOD↔D 被覆の非対称是正 | FND-100 | ✅ resolved（2026-06-21）。D-5→DM-3 拡張（v0.2）・D-7→TERM-5/DM-5（CoverageReport）・D-17〜D-21→TERM-6/DM-6（InspectionViews）新設・MOD-1 v0.3。config 規則変更なし（伝播チェック不要）。🟡 注記（MOD→[P\|D] OR 化の型別強制喪失）は FND-96 選択肢A 決定済みトレードオフとして記録 |
| FND-96 設計修正 — DM→MOD→D 正規化（選択肢A・sprint-1） | FND-96 | ✅ resolved（2026-06-20）。config.yaml 変更（MOD→[P\|D]・DM→MOD）・MOD-1 辺変更（v0.1→v0.2）・TERM-1〜4/DM-1〜4 新設 |
| FND-99 著作資産の規則伝播ギャップ是正 — スキル/エージェント/接続マトリクスを config に同期 | FND-99 | ✅ resolved（2026-06-20）。FND-96（MOD→[P\|D]・DM→MOD）・DD-15（ORC→E）の規則を7資産に伝播。design-author 等が旧ルールの辺を再生産する穴を解消 |
| PR #28 レビュー対応：ORC-1 と DD-15 の矛盾（FND-97）・ダッシュボード陳腐化（FND-98） | FND ×2 | ✅ resolved（2026-06-20）。ORC-1 P 辺 6 本を削除（v0.3→v0.4）・ダッシュボード 3 箇所更新・PR 本文更新 |
| 設計層（凍結セット）着手（N2）：MOD-1〜18 / PORT-1 / DS-1〜3 / PRS-1 / ORC-1〜2 著作・反映。DD-13 v0.3 改訂・DD-14・DD-15 起票。current_stage→design | N2 | ✅ done（2026-06-20）。design-author→reconciliation 完了。`doc-system/05-design/` 新設。config.yaml current_stage=design |

> 完了済みの旧作業（〜2026-06-16：DD-12 分析層見直し／PR #27／N1／N8／FND-92/80/85〜91／全 SPEC 自己点検／FND-40〜77）は本表から除去。経緯は DD/FND ノードと「推奨ネクストアクション」の完了済み行に保全（消さない＝PR8）。

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | 備考 |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 250 | ✅ 著作・点検済 | VERIFY-2/5。本文品質 FND-40〜77 をテスタブル化分割（SPEC 子展開で 213 ノード・うち post-mvp 25）。**FND-102（issue #30・②）で必須辺 44 行を全 dedicated SPEC 化：SPEC-56/57/58 傘＋36 子・SPEC-18-6〜8・SPEC-28-3 を新設（+39）**。**FND-103 案②で SPEC-18-9（fnd_lifecycle.resolved.must_be_linked_from）を新設（+1）。SPEC-59（must_not_link_to）は FND-104 の RULE 決定待ちで保留** |
| analysis | ACTOR / I / O / D / P / E | 92 | ✅ **current stage**・著作/点検済 | DD-12 全面見直し：D-9〜D-22 分割（+14）・P-1〜P-7 全リーフ分解（+39）・P-2-5 新設・I-1-1/1-2/1-3 退役（-3）。O-6 終了コード追加（FND-95・PR#27 ③）。00-dfd.md を L0–L3 で再生成 |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 31 | 🔄 進行中 | N2 着手（2026-06-16）。MOD-1〜18 / PORT-1 / DS-1〜3 / PRS-1 / ORC-1〜2 著作済み。FND-96（DM→MOD→D 正規化）resolved（2026-06-20）：DM-1〜4 / TERM-1〜4 新設・config.yaml 修正・MOD-1 v0.2。**FND-100（PR #32・DM↔MOD↔D 被覆対称化）resolved（2026-06-21）：DM-5（CoverageReport）/ DM-6（InspectionViews）/ TERM-5/6 新設・DM-3 v0.2・MOD-1 v0.3**。テスト戦略 ④ 未着手 |
| implementation | SRC（spec-inspector・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビュー VERIFY-1〜5 は実施済 |
| 横断スパイン | DD / Q / PEND | 22 | ✅ | DD-1〜16（DD-16: FND 専用ライフサイクルルール・Q-4 から昇格）・Q-1/Q-4 closed・Q-2/Q-3 open・PEND-1 resolved・PEND-2 deferred |

> 凡例：✅ 完了／🔄 進行中／⬜ 未着手。ノード数は `-N` 子・`labels: post-mvp` を含む実数。
> current_stage が `design` に進行（N2・2026-06-16）。design 発火の辺ルール（MOD→P / PORT→MOD / DS→P / PRS→DS / ORC→E）が全ノードに適用中（DD-15 により ORC→P から ORC→E に変更）。

---

## 🔥 推奨ネクストアクション

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N3 | 実装（FR-10：spec-inspector CLI） | 🔵 低 | Python 標準ライブラリのみ。凍結セット確定後（テスト戦略 ④ 完了後） |
| N12 | テスト戦略 ④（凍結セット残項目） | 🟡 中 | 設計 25 ノード著作済み。`/test-strategy` スキルで TD/TC 設計。凍結セット完了前に N3 着手しない |
| N11 | 03-spec.md 残課題 FND-79/81/82/83/88/89/91（INFO 7件）の実施スプリント決定 | 🔵 低 | 全 INFO・`scheduled` 未設定。オーナー判断待ち（独断繰り越し禁止） |

> **完了済み（経緯は DD/FND ノードに保全・PR8）**: **N2（設計層着手・MOD-1〜18/PORT-1/DS-1〜3/PRS-1/ORC-1〜2 著作・DD-13 v0.3 改訂/DD-14/DD-15・current_stage→design・2026-06-20）**／**N1（current_stage→analysis・2026-06-15）／N8（O-4/O-5/P-8/P-9 補完・FND-92・2026-06-15）**／N0（VERIFY-2 再点検）／N4（PEND-1 resolved）／N5（VERIFY-3・P 単一責務）／N6（DD-5・NFR→SPEC 導出）／N7（FND-18・SPEC-52/53・RULE-028）／N9・N10（VAL-5/6・SR-8/9 を sprint-2 起票）／DFD 生成（03-analysis/00-dfd.md）／**分析層全面見直し（DD-12・FND-93/94・I-1-x 退役・DFD 再生成・2026-06-16）**／PR #21・#22 レビュー（FND-24〜39）。

---

## ⏳ オーナー判断待ち

**計 6 件**

| 項目 | 優先 | 種別 | 次アクション |
|---|---|---|---|
| Q-2：傘 SPEC（SPEC-21/25/1・SPEC-29）の細分化要否＋ SPEC-29-1/29-2 リーフマップ | 🟡 中 | Q | 推奨 A（傘マップ維持・実害顕在時に細分化）。方針・実施スプリントはオーナー判断。`scheduled` 未設定 |
| Q-3：O-1/O-2 の生成元辺を P-4-3（リーフ）へ精緻化するか親 P-4 のままか | 🔵 低 | Q | 推奨 A（リーフ先例 O-3/O-6・フロー表に統一・最小変更）。採否・実施スプリントはオーナー判断。`scheduled` 未設定 |
| FND-101：resolved FND（FND-1〜95）の元 forward 辺残留（辺逆転違反） | 🟡 中 | FND | Q-4 → DD-16 決定（2026-06-21）により是正可能。別ブランチ実施。実施スプリントはオーナー判断。`scheduled` 未設定 |
| 03-spec.md 残課題 FND-79・81・82・83・88・89・91（計7件・open） | 🟡 中 | FND | 横断整合＋自己点検残課題の実施スプリント決定（全 INFO）。`scheduled` 未設定 |
| FND-103：fnd_lifecycle resolved 系2ルールの dedicated SPEC 化（案②・責務分離） | 🔵 低 | FND | オーナー決定＝案②採用。`must_be_linked_from`＝SPEC-18-9 反映済み。`must_not_link_to`＝SPEC-59 は FND-104 の RULE 決定待ちで保留 |
| FND-104：must_not_link_to を検出する RULE が未定義（検出機構の空白） | 🟡 中 | FND | 案A（RULE-006 拡張）／**案B 推奨（新規 RULE-030 新設・責務分離）**。SPEC-59 が引く RULE を確定するため。実施時期もオーナー判断・`scheduled` 未設定 |

> N1（current_stage→analysis）は 2026-06-15 オーナー指示で実施済み。
> FND-102（issue #30・必須辺の仕様化漏れ点検）はオーナー決定＝選択肢②で **resolved**（2026-06-21・SPEC-56/57/58＋SPEC-18-6〜8・SPEC-28-3 新設で 44 行全 dedicated SPEC 化）。

---

## 📋 FND サマリ

**計 104 件：✅ resolved 93 ／ ⏳ open 11**

> 本文品質 FND-40〜77（38件）は各 SPEC の `期待動作` を「`【条件】のとき、〇〇を▲▲する`」の単一アサーション子 SPEC へ `-N` 分割して全解消。親はアンブレラ化し可視バッジ据置（DD-8 z-bump）・子は親バッジ x.y を ref_version 参照。FND-78（DD-9）・FND-84（DD-10）も resolved。**FND-85〜91** は全 SPEC 自己点検（spec-inspector ×6）で surfaced した残課題（オーナー判断: 全件起票）。うち **FND-80/85/86/87/90 を即処置（resolved・2026-06-15・DD-11 新設・SPEC-55 新設）**。**FND-92**（N8 で顕在化した E-1 本文と P-8/P-9・O-4/O-5 の不整合）も即 resolved（E-1 本文改訂・`--coverage`/P-3-2 先例と整合・新 E 不要・DD-8 §4 z バンプ据置）。**FND-93/94**（分析層全面見直しで顕在化：FND-93＝旧 D-4 の condition/result/log_ref 欠落による価値経路断絶／FND-94＝総点検 G1・G4 の被覆ドリフト）も即 resolved（2026-06-16・DD-12）。**FND-95**（PR #27 レビュー③：P-4-4 終了コードの O/D 未モデル＝PR6 価値経路の穴）も O-6「終了コード」新設で resolved（2026-06-16）。**FND-96**（設計層 DM→MOD→D チェーン欠落＝PR1）は選択肢A フル実施で resolved（2026-06-20・config.yaml + MOD-1 + TERM-1〜4 + DM-1〜4）。**FND-97/98**（PR #28 レビュー：ORC-1 P 辺の DD-15 違反／ダッシュボード・PR 本文の陳腐化）は即 resolved（2026-06-20・ORC-1 v0.4・本帳票更新）。**FND-99**（設計接続規則の決定 FND-96/DD-15 が out-of-graph 著作資産＝スキル/エージェント/接続マトリクスに未伝播だったドリフト）も即 resolved（2026-06-20・7資産を config.yaml の正ルール `MOD→[P\|D]`／`DM→MOD`／`ORC→E` に同期）。**FND-100**（PR #32 レビュー：FND-96 処置後の DM↔MOD↔D 被覆の非対称＝D-17〜D-21 に対応 DM 不在・D-5/D-7 も非対称）も即 resolved（2026-06-21・DM-3 拡張＋DM-5 CoverageReport／DM-6 InspectionViews／TERM-5/6 新設・MOD-1 v0.3。config 規則変更なしで伝播チェック不要。🟡 OR 化トレードオフは FND-96 選択肢A 決定済みとして記録）。**FND-99 は v0.2 に改訂**（2026-06-21・辺逆転ルール DD-3 適用＝元 forward 辺 `→FND-96`/`→DD-15` を削除し `edges: []`・指摘時 ref_version は本文へ移動。処置対象が out-of-graph 資産でバックリファレンス対象が未著作のため、恣意的抑制を行わず RULE-005 完全孤立を意図的に保持＝「resolved だがバックリファレンス対象未著作」の正しいシグナル）。**FND-101**（resolved FND の大部分 FND-1〜95 が元 forward 辺を削除せず辺逆転ルール違反＝double-edge 残置・サイレントな構造的負債）も起票（open・是正は Q-4 決定依存で別ブランチ・`scheduled` 未設定）。INFO の残 open（FND-79/81/82/83/88/89/91）は全て `scheduled` 未設定。**FND-102**（issue #30「必須辺の仕様化漏れ点検」：config 44 行のうち dedicated SPEC は当初 8 行のみ・残 36 行は parametric 傘仕様 SPEC-8 依存）は **resolved**（2026-06-21・オーナー決定＝選択肢②「全 44 行を dedicated SPEC 化」。SPEC-56/57/58 傘＋36 子・SPEC-18-6〜8・SPEC-28-3 を新設し全行 1:1 トレーサビリティ成立。新設傘 SPEC-56/57/58 に `→FND-102` backref・forward 辺は baseline 慣行どおり保持で FND-101/Q-4 辺逆転コホートに帰属）。**SPEC-18-1（FND→any）は origin/main マージで `must_link_to` 標準セクションから `fnd_lifecycle.unresolved.must_link_to` へ移動したため標準 44 行外**（FND→any 系の dedicated 化＝fnd_lifecycle 残2ルールは別途 FND-103 で追跡）。なお形式的な行→SPEC 索引表は FND-79（分散→索引化・open）の領分で別途検討。**FND-103**（fnd_lifecycle の必須辺ルール3つのうち resolved 系2ルール〔must_be_linked_from／must_not_link_to〕が dedicated SPEC を欠く被覆均一化の残課題）を起票（open・INFO・FND-79／FND-101／Q-4 辺逆転コホートと同系統）。**FND-103 はオーナー決定＝案②（責務分離）で処置中：`must_be_linked_from`（辺欠如/error）に SPEC-18-9 を新設・反映済み。`must_not_link_to`（辺残留/warning）は SPEC-59 を著作したが、その処置中に config `fnd_lifecycle.resolved.must_not_link_to` を検出する RULE が 05-verification.md に未定義（RULE-006＝欠如のみ／RULE-001/022＝decision_spine ノード型固有・汎用辺残留 RULE が空白）と判明したため FND-104（WARNING・open）を起票し、SPEC-59 は RULE 確定まで保留。FND-103 の完全 resolved は FND-104 の RULE 決定後。** WARNING の open は FND-35（sprint-2 承認済）・FND-101（Q-4 決定依存）（FND-96 は 2026-06-20 resolved）。明細は `04-verification/02-findings.md`。

### open 明細（11 件）

| ID | 深刻度 | 状態 | 概要 |
|---|---|---|---|
| FND-35 | WARNING | 🗓 sprint-2（承認済） | config `SPEC→SPEC` OR ループホール（推奨 ②＋③） |
| FND-101 | WARNING | ⏳ open | resolved FND（FND-1〜95）が元 forward 辺を削除せず辺逆転違反（double-edge）。是正は Q-4 決定依存・別ブランチ・`scheduled` 未設定 |
| FND-79 | INFO | ⏳ open | RULE-006/025/026 が複数 SPEC に分散 → 索引化 |
| FND-81 | INFO | ⏳ open | SPEC-31 の親が FR-1 だが trace_scope 主題の FR-9 が自然 |
| FND-82 | INFO | ⏳ open | SPEC-9-1 と SPEC-10 が RULE-004 で近接 → 統合検討 |
| FND-83 | INFO | ⏳ open | always_error SPEC の condition 不揃い（SPEC-6=error/SPEC-7=failure） |
| FND-88 | INFO | ⏳ open | SPEC-13 の condition が入力/トリガ側にあり期待動作の文頭に来ていない |
| FND-89 | INFO | ⏳ open | アンブレラ SPEC-44 の condition=normal が子（boundary/error）を代表せず |
| FND-91 | INFO | ⏳ open | SPEC-3-1 が人手採番で機械観測が弱く `例` 欠落 |
| FND-103 | INFO | ⏳ open | 案②採用（責務分離）。`must_be_linked_from`＝**SPEC-18-9 反映済み**。`must_not_link_to`（辺残留）は **FND-104 の RULE 決定待ちで SPEC-59 保留**。完全 resolved は RULE 確定後 |
| FND-104 | WARNING | ⏳ open | config `fnd_lifecycle.resolved.must_not_link_to`（辺残留/warning）を検出する RULE が 05-verification.md に未定義（RULE-006＝欠如のみ・RULE-001/022＝ノード型固有）。SPEC-59 が引く RULE を決められない。推奨②新規 RULE 新設・オーナー判断待ち・`scheduled` 未設定 |

---

## 🔁 VERIFY サマリ

| ID | 対象 | 実施日 |
|---|---|---|
| VERIFY-1 | 要件〜分析層 | 2026-06-11 |
| VERIFY-2 | N0 再点検 | 2026-06-12 |
| VERIFY-3 | N5・P 単一責務点検 | 2026-06-13 |
| VERIFY-4 | PR #21 オーナーレビュー | 2026-06-13 |
| VERIFY-5 | requirements 層追加バッチ | 2026-06-14 |

> いずれも `suppress: [RULE-004]` 付与済み（DD-2 決定・凍結記録）。

---

## 🧭 DD / Q / PEND サマリ

| ID | 状態 | 概要 |
|---|---|---|
| DD-1〜5 | ✅ 反映済 | 決定・本文反映完了 |
| DD-6 | ✅ 反映済 | spec 層＋分析層（O-4/O-5/P-8/P-9）著作・反映完了（2026-06-15／N8）。FND-92 で E-1 整合 |
| DD-7 | ✅ 反映済 | 分析層 DFD 改訂（D 起票／並走著作／退役 ID 不再利用） |
| DD-8 | ✅ 反映済 | ノードバージョニング正式化・フロントマター全廃・ref_version 一括移行（170 件・ドリフト 0） |
| DD-9 | ✅ 反映済 | config phases から post-mvp 除去・RULE-029 新設（FND-78） |
| DD-10 | ✅ 反映済 | SPEC-47 をノードバッジ x.y 検証に置換・NFR-1/SPEC-44 訂正（FND-84） |
| DD-11 | ✅ 反映済 | 自己点検残課題 FND-85/86/87/90 の即処置決定 |
| DD-12 | ✅ 反映済 | 分析層全面見直し：D-3/D-4 内部化＋D-9〜D-22 分割／P-2-5 発火制御一元化／I-1-1/1-2/1-3 退役／リーフ単一動詞分解（2026-06-16） |
| DD-13 | ✅ 反映済 | MOD 粒度：孫プロセスあり OR 責務別→L2 分割（C 案・v0.3）。MOD-1〜18 で採用（2026-06-20・v0.3 で →FND-98 backref） |
| DD-14 | ✅ 反映済 | FileSystemPort 抽象化粒度：単一 Port（A 案）。list_md_files + read_file の 2 メソッド Protocol（2026-06-16） |
| DD-15 | ✅ 反映済 | ORC の must_link_to 参照先を P→E に変更（設計ノードの上流参照を起動イベントへ）。config.yaml must_be_linked_from 追加・ORC-1〜2 適用（2026-06-18） |
| DD-16 | ✅ 反映済 | FND 専用ライフサイクルルールを config に独立定義（Q-4 から昇格・選択肢A・2026-06-21）。config.yaml `fnd_lifecycle` 新設・FND-96/97/98/100 suppress 撤去・resolved フィールド導入 |
| Q-1 | ✅ closed | DD-2 へ昇格済み |
| Q-2 | ⏳ open | 傘 SPEC 細分化要否＋ SPEC-29-1/29-2 リーフマップ。推奨 A（傘維持）。オーナー判断待ち |
| Q-3 | ⏳ open | O-1/O-2 生成元辺の粒度（親 P-4 vs リーフ P-4-3）。推奨 A（P-4-3 へ精緻化）。オーナー判断待ち |
| Q-4 | ✅ closed | DD-16 へ昇格済み（2026-06-21・選択肢A 採用） |
| PEND-1 | ✅ resolved | 過分割 → 子ノード化（FND-6）→ DD-12 で I-1-x 退役・D-18 へ repoint |
| PEND-2 | 🗓 deferred | 図のスクリプト生成は VAL-5/FR-15 で sprint-2 以降 |
| DD19（review-system） | ✅ 確定 | asset-lateral-deploy スクリプト廃止・エージェント手書き化。DD18 superseded（2026-06-15） |

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- **状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。

## 参考ドキュメント
- **グローバル設定**: [`docs/doc-system/config.yaml`](../../../docs/doc-system/config.yaml) — 必須接続ルール・ステージ・condition 語彙・カバレッジ要件
- **RULE 定義**: [`docs/doc-system/05-verification.md`](../../../docs/doc-system/05-verification.md) — RULE-001〜029 の完全定義
- **記法ガイド**: [`docs/doc-system/04-notation.md`](../../../docs/doc-system/04-notation.md) — ノード埋め込み・summary バッジ（ノードバージョン x.y）・YAML ブロック形式
