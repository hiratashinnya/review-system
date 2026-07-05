# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> **状態と優先度の要約**に絞る——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は要約のみ。**全件列挙はしない**。
>
> **最終更新**: 2026-07-01 ｜ **current_stage**: `design`（`docs/doc-system/config.yaml`）
> 直近: **issue #64（backref check 既存 18 ERROR 是正）を処置（2026-07-01）**。うち **8件（Category A）は `backref/check.py` 自体のバグ**（`open-but-backref-exists` 判定がトートロジーで open FND を全件誤検出）と判明し実在の不整合ではなかった（FND-112・check.py 修正＋回帰テスト追加）。誤検出のまま `backref reverse --apply` していればオーナー承認済み sprint-2 の FND-35 を独断で resolved 化する破壊的操作になっていた。残り本物の10件（Category B/C：FND-17/37/38/94/98/100/106/107/111）は DD-3 マーカー追記・付与先なし明記で是正。副次的に FND-94 の本文フォーマット不整合（内部 `---` 誤用によるノード境界パーサの截断）も発見・是正（z バンプ）。`python -m backref check` は 18→0 件。詳細は FND-112。
> 直近（設計層）: **設計層 static ノードを上流から作りきり（2026-06-30）**。設計層に欠けていた SCM（スキーマ・10）・CFG（設定・1要素1ノード・14）・PROMPT（著作支援プロンプト・7）の計 **31 ノード**を著作し `05-design/05-static.md` 新設。**PROMPT が N/A という分析は誤りで訂正**＝著作支援（P-7-1）は LLM（`*-author`）でプロンプトを持つ（SPEC-27/FR-13 を実現・PROMPT-6＝reconciliation 書込／PROMPT-7＝reconciliation-validator 検証→SPEC-39）。**PR#55 レビューで「1 LLM エージェント=1 PROMPT」粒度の取りこぼし（validator 欠落）を発見し PROMPT-7 を追補**。設計層 31→62 ノード（＋TERM-1〜6）。次は **テスト戦略④の要否判断 → 実装**。

---

## 🔄 直近の作業

| 作業 | 種別 | 状態 |
|---|---|---|
| issue #68 — ノード本文中の孤立 `---` 截断の予防 lint（PR #65 follow-up） | SPEC-62/-1/-2（新規）／`backref/notation.py`／Q-6 是正 | ✅ 完了（2026-07-02）。`04-notation`/SCM-1-2 の「`---`＝ノード分離専用」に反する**本文内 `---` が本文を silent 截断**する問題を検出する lint を **spec-first**（SPEC-62 傘＋62-1 正常/62-2 failure→FR-1）で実装：`backref check` に `stray-hr-in-body` 監査を追加（次非空行が 見出し/`<details>`/`>` のいずれでもない `---` を WARNING）。検出器が**私の Q-6 の本文截断（論点/①/②が脱落）**を発見→是正（内部 `---` 除去＋`## `→`### `・v0.2.1）。テスト2件追加・全205 pass。明細＝SPEC-62／Q-6 |
| issue #64 — `backref check` 既存18 ERROR 是正 | FND-112 resolved（新規）／FND-17・37・38・94・98・100・106・107・111 是正 | ✅ 完了（2026-07-01）。**Category A（8件）は `backref/check.py` のトートロジーバグによる誤検出**と判明（実在の不整合ではない・FND-35 等の open FND は不可触）。check.py の `open-but-backref-exists` 判定を修正＋回帰テスト追加。**Category B/C（10件）は本物**：resolved-no-dd3（6件）に DD-3 マーカー追記、resolved-no-backref（4件）に付与先なし明記。副次的に FND-94 の内部 `---` 誤用（ノード境界パーサ截断）も発見・是正。`backref check` 18→0 件。明細＝FND-112／findings.md |
| skill の設計層モデリング拡張（Q-6→DD-22） | DD-22 / FR-17 / SPEC-61 / PROMPT-8〜20 | 🔄 sprint-1・②著作完了（2026-07-01）。機能軸 **FR-17＋傘 SPEC-61/-1/-2/-3** 新設、価値実現直結の **skill 13件を PROMPT-8〜20** に PROMPT 化（`carrier: skill`・→SPEC-61）。全ノード在グラフ・drift/孤立/重複なし・新規起因エラーゼロで機械検証済。**残＝①-C の `.claude/` fan-out 実装**（対話入口 skill／非対話 fan-out orchestrator agent）＋carrier スキーマ化・対象 skill 集合宣言・検査 RULE 新設要否（FND/Q 起票予定）。明細＝DD-22 |
| A2 — resolved-flag ドリフト一括是正（「本文 resolved／機械 unresolved」19件に A-1 同型の辺逆転を適用） | FND-111 resolved | ✅ 完了（2026-06-29）。`resolved: true` 欠落19件（FND-17/18/24/25/26/27/28/31/33/36/78/84/85/86/92/93/94/102/106）を `resolved: true`＋`edges: []` 化、in-graph 処置対象へ backref（新規7・既存14＝double-edge 解消）・provenance 辺（DD/FND/Q）は本文記録のみ・全 **z バンプ**（DD-21）。機械 `resolved: true` を 81→101 件へ整合。**FND-99/108 は意図的孤立設計のため不可触**。FND-106/111 は incoming なしで意図的孤立保持。明細＝FND-111／findings.md |
| A-1 — FND-101 辺逆転一括是正（resolved FND の double-edge 解消） | FND-101 resolved / DD-16 / Q-4 closed | ✅ 完了（2026-06-28）。resolved FND 75件の元 forward 辺削除・`edges: []`・`resolved: true` 化・指摘時 ref_version を本文へ移動（DD-3）・全 z バンプ（DD-21）。明細＝FND-101／DD-21 |
| FND-96〜100 バンプ是正（MINOR→z・A-1 以前の pre-existing ドリフト） | FND-110 / DD-21 / issue #40 | ✅ resolved（2026-06-28）。FND-96=v0.4.1・FND-97/98/99/100=v0.1.1 へ z バンプ訂正。DD-21 残課題コホート完了。明細＝FND-110 |
| A-2 — O-1/O-2 生成元辺のリーフ精緻化（Q-3→DD-20 昇格）＋横断スパイン ✅ 表記是正 | DD-20 / Q-3 closed / FND-79 | ✅ 完了（2026-06-24）。O-1/O-2 生成元辺を `→P-4`→リーフ `→P-4-3` へ精緻化（O 型粒度をリーフ基準で統一）。横断スパイン完成度の ✅↔未決矛盾は FND-79 スコープへ吸収し 🔄 へ是正。明細＝DD-20 |

> 完了済みの旧作業（〜2026-06-23）は本表から除去。経緯は DD/FND ノードに保全（消さない＝PR8）：PR #37（FND-106/DD-19・検証トリガ統一）／FND-105・SPEC-60（resolved 判定セマンティクス）／FND-103/104・DD-17（resolved 系2ルール dedicated 化・RULE-030）／FND-102（issue #30・必須辺44行 dedicated 化）／DM-3 v0.3／DD-16・Q-4（fnd_lifecycle 正式化）／FND-96〜100（設計層 DM→MOD→D 正規化・PR #28/#32 レビュー）／N2（設計層着手・current_stage→design）／〜2026-06-16（DD-12 分析層見直し・FND-40〜77・全 SPEC 自己点検 ほか）。

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | 備考 |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 263 | ✅ 著作・点検済 | **2026-07-02 ノード本文截断 lint の機能仕様 SPEC-62＋62-1/62-2（+3・FR-1 配下・Issue #68）**：本文中の孤立 `---` を検出し WARNING（実装＝`backref/notation.py`）。**2026-07-01 skill プロンプト資産の機能軸 FR-17＋傘 SPEC-61/-1/-2/-3（+5・DD-22）**：skill を PROMPT 設計ノード化する要件（存在/親辺/キャリア属性）。著作エージェント軸 SPEC-27/FR-13 とは別軸。 VERIFY-2/5。本文品質 FND-40〜77 をテスタブル化分割（SPEC 子展開で 213 ノード・うち post-mvp 25）。**FND-102（issue #30・②）で必須辺 44 行を全 dedicated SPEC 化：SPEC-56/57/58 傘＋36 子・SPEC-18-6〜8・SPEC-28-3 を新設（+39）**。**FND-103 案②（責務分離）で fnd_lifecycle resolved 系2ルールを全 dedicated 化：SPEC-18-9（must_be_linked_from・辺欠如/error）＋ SPEC-59（must_not_link_to・辺残留/warning・RULE-030 経由）を新設（+2）**。**FND-105 で resolved 判定セマンティクスを dedicated 化：SPEC-60 傘＋SPEC-60-1/60-2 を FR-7 配下に新設、さらに型検証スコープ外を撤回し SPEC-60-3（resolved 非 boolean→RULE-031 ERROR）を追加（+4・60 傘/60-1/60-2/60-3）** |
| analysis | ACTOR / I / O / D / P / E | 92 | ✅ **current stage**・著作/点検済 | DD-12 全面見直し：D-9〜D-22 分割（+14）・P-1〜P-7 全リーフ分解（+39）・P-2-5 新設・I-1-1/1-2/1-3 退役（-3）。O-6 終了コード追加（FND-95・PR#27 ③）。00-dfd.md を L0–L3 で再生成 |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 75 | 🔄 ほぼ完成 | MOD-1〜18 / PORT-1 / DS-1〜3 / PRS-1 / ORC-1〜2 / DM-1〜6 / TERM-1〜6 著作済み。**2026-06-30 静的設計ノードを上流から作りきり（`05-static.md`・+31）**：SCM-1〜3 系（10）／CFG-1＋1-1〜1-13（14）／PROMPT-1〜7（著作支援＝`*-author`×5→SPEC-27・reconciliation＋validator→SPEC-39）。**2026-07-01 skill 軸 PROMPT-8〜20（+13・DD-22）**：価値実現直結の 13 skill を機能軸 FR-17／傘 SPEC-61 配下に PROMPT 化（`carrier: skill`・→SPEC-61）。skill｜agent はキャリア属性で表し将来の agent 化は carrier＋版で吸収。残り：①-C の `.claude/` fan-out 実装・テスト戦略④の要否判断・D ロギング |
| implementation | SRC（spec-inspector・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビュー VERIFY-1〜5 は実施済 |
| 横断スパイン | DD / Q / PEND | 30 | 🔄（一部未決） | DD-1〜22（DD-16: FND 専用ライフサイクル／DD-17: RULE-030 新設・案B・FND-104／DD-18: RULE-031 新設・案B・FND-105 型検証／DD-19: 検証トリガ統一・案A・FND-106／DD-20: O-1/O-2 生成元辺を P-4-3 へ精緻化・案A・Q-3 昇格／DD-21: resolved-FND 辺逆転/backref は z バンプ・案A・Q-5 昇格・D 却下／DD-22: skill の設計層モデリング拡張＝①-C ハイブリッド＋②-A PROMPT 流用・Q-6 昇格・2026-07-01）・Q-1/Q-3/Q-4/Q-5/Q-6 closed・**Q-2 open**・PEND-1 resolved・**PEND-2 deferred**。未決ノード（Q-2 open・PEND-2 deferred）が残るため ✅ ではなく 🔄 とする（FND-79 索引・表記精度スコープで是正） |

> 凡例：✅ 完了／🔄 進行中／⬜ 未着手。ノード数は `-N` 子・`labels: post-mvp` を含む実数。
> current_stage が `design` に進行（N2・2026-06-16）。design 発火の辺ルール（MOD→P / PORT→MOD / DS→P / PRS→DS / ORC→E）が全ノードに適用中（DD-15 により ORC→P から ORC→E に変更）。

---

## 🔥 推奨ネクストアクション

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N3 | 実装（FR-10：spec-inspector CLI） | 🔵 低 | Python 標準ライブラリのみ。凍結セット確定後（テスト戦略 ④ 完了後） |
| N12 | テスト戦略 ④（凍結セット残項目） | 🟡 中 | 設計 25 ノード著作済み。`/test-strategy` スキルで TD/TC 設計。凍結セット完了前に N3 着手しない |
| N11 | 03-spec.md 残課題 FND-79/81/82/83/88/89/91（INFO 7件）の実施スプリント決定 | 🔵 低 | 全 INFO・`scheduled` 未設定。オーナー判断待ち（独断繰り越し禁止） |


> **完了済み（経緯は DD/FND ノードに保全・PR8）**: **設計層 static 作りきり（SCM10・CFG14・PROMPT7＝計31・`05-static.md`・PROMPT N/A 撤回・PR#55 レビューで PROMPT-7 validator 追補・2026-06-30）**／**A2（FND-111・resolved-flag ドリフト19件の A-1 同型辺逆転・機械 resolved:true 81→101・2026-06-29）**／**A-1（FND-101・double-edge 75件解消・2026-06-28）／FND-110（FND-96〜100 バンプ是正・DD-21・2026-06-28）**／**N13（FND-107 処置・ノードバージョン x.y→x.y.z 移行・案 A 実施・2026-06-23）**／**N2（設計層着手・MOD-1〜18/PORT-1/DS-1〜3/PRS-1/ORC-1〜2 著作・DD-13 v0.3 改訂/DD-14/DD-15・current_stage→design・2026-06-20）**／**N1（current_stage→analysis・2026-06-15）／N8（O-4/O-5/P-8/P-9 補完・FND-92・2026-06-15）**／N0（VERIFY-2 再点検）／N4（PEND-1 resolved）／N5（VERIFY-3・P 単一責務）／N6（DD-5・NFR→SPEC 導出）／N7（FND-18・SPEC-52/53・RULE-028）／N9・N10（VAL-5/6・SR-8/9 を sprint-2 起票）／DFD 生成（03-analysis/00-dfd.md）／**分析層全面見直し（DD-12・FND-93/94・I-1-x 退役・DFD 再生成・2026-06-16）**／PR #21・#22 レビュー（FND-24〜39）。

---

## ⏳ オーナー判断待ち

**計 2 件**

| 項目 | 優先 | 種別 | 次アクション |
|---|---|---|---|
| Q-2：傘 SPEC（SPEC-21/25/1・SPEC-29）の細分化要否＋ SPEC-29-1/29-2 リーフマップ | 🟡 中 | Q | 推奨 A（傘マップ維持・実害顕在時に細分化）。方針・実施スプリントはオーナー判断。`scheduled` 未設定 |
| 03-spec.md 残課題 FND-79・81・82・83・88・89・91（計7件・open） | 🟡 中 | FND | 横断整合＋自己点検残課題の実施スプリント決定（全 INFO）。`scheduled` 未設定 |

> N1（current_stage→analysis）は 2026-06-15 オーナー指示で実施済み。
> FND-102（issue #30・必須辺の仕様化漏れ点検）はオーナー決定＝選択肢②で **resolved**（2026-06-21・SPEC-56/57/58＋SPEC-18-6〜8・SPEC-28-3 新設で 44 行全 dedicated SPEC 化）。

---

## 📋 FND サマリ

**計 112 件：✅ resolved 104 ／ ⏳ open 8**（機械 `resolved: true` 101 件。FND-99/108/106/112 は意図的孤立設計または FND-102 baseline 慣行のため本文 resolved のまま `resolved: true` を省略＝documented）

> **FND-112**（2026-07-01・issue #64 検証中に発見・resolved）: `backref/check.py` の `open-but-backref-exists` 判定がトートロジーで open FND 全件を誤検出していたバグ。指摘対象が out-of-graph（check.py）のため `resolved: true` 省略・FND-102/106 baseline 慣行。明細＝findings.md FND-112。

> **要約**（全件列挙はしない＝明細は [`04-verification/02-findings.md`](04-verification/02-findings.md) を参照・PR8 で各 FND ノードに経緯保全）。主な resolved 経緯：本文品質 FND-40〜77（38件）は子 SPEC `-N` 分割で全解消（DD-8 z-bump）／自己点検残課題 FND-78・80・84〜91（spec-inspector ×6・DD-9/10/11・SPEC-55）／分析層見直し FND-92〜95（DD-12・O-6 新設）／設計層 DM→MOD→D 正規化と PR #28/#32 レビュー FND-96〜100（TERM/DM 新設・MOD-1・7資産同期）／必須辺44行 dedicated 化 FND-102（SPEC-56/57/58＋）・resolved 系2ルール FND-103/104（SPEC-18-9/59・RULE-030・DD-17）・resolved 判定セマンティクス FND-105（SPEC-60・RULE-031・DD-18）・検証トリガ統一 FND-106（DD-19）／ノード版 x.y.z 化 FND-107〜109（PR #38）。
> **lifecycle 辺逆転コホート**：**FND-101**（A-1・resolved FND 75件の double-edge 一括解消・2026-06-28）→ **FND-110**（FND-96〜100 の MINOR→z バンプ是正・DD-21・2026-06-28）→ **FND-111**（`resolved: true` 欠落19件に A-1 同型の辺逆転を適用＝「本文 resolved／機械 unresolved」ドリフトを解消・2026-06-29）。版バンプは全て **z**（DD-21・DD-8 §4「backref/lifecycle 操作＝z」）。**FND-99/108 は意図的孤立設計（forward 辺なし）を保持し不可触**。
> INFO の残 open（FND-79/81/82/83/88/89/91）は全て `scheduled` 未設定（オーナー判断待ち）。

### open 明細（8 件）

| ID | 深刻度 | 状態 | 概要 |
|---|---|---|---|
| FND-35 | WARNING | 🗓 sprint-2（承認済） | config `SPEC→SPEC` OR ループホール（推奨 ②＋③） |
| FND-79 | INFO | ⏳ open | RULE-006/025/026 が複数 SPEC に分散 → 索引化（＋横断スパイン ✅ 表記矛盾の索引精度をスコープに吸収・v0.1.1） |
| FND-81 | INFO | ⏳ open | SPEC-31 の親が FR-1 だが trace_scope 主題の FR-9 が自然 |
| FND-82 | INFO | ⏳ open | SPEC-9-1 と SPEC-10 が RULE-004 で近接 → 統合検討 |
| FND-83 | INFO | ⏳ open | always_error SPEC の condition 不揃い（SPEC-6=error/SPEC-7=failure） |
| FND-88 | INFO | ⏳ open | SPEC-13 の condition が入力/トリガ側にあり期待動作の文頭に来ていない |
| FND-89 | INFO | ⏳ open | アンブレラ SPEC-44 の condition=normal が子（boundary/error）を代表せず |
| FND-91 | INFO | ⏳ open | SPEC-3-1 が人手採番で機械観測が弱く `例` 欠落 |

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
| DD-17 | ✅ 反映済 | `fnd_lifecycle.resolved.must_not_link_to`（辺残留/warning）検出に**新規 RULE-030 を新設**（案B・FND-104・2026-06-22）。欠如=RULE-006／残存=RULE-030 で責務分離。05-verification.md 段階①に追加・SPEC-59 が RULE-030 を引く |
| DD-18 | ✅ 反映済 | `resolved` の boolean 型検証（SPEC-60-3）に**新規 RULE-031 を新設**（案B・FND-105・2026-06-23）。共通必須型=RULE-028／型別任意型=RULE-031 で責務分離（condition→RULE-016・result→RULE-020 の「型別フィールドは専用 RULE」パターン）。05-verification.md 段階0 に ERROR・非 fail-close で追加・SPEC-60-3 が RULE-031 を引く・`edges: []` |
| DD-19 | ✅ 反映済 | 検証戦略の段階別トリガを §1 フロー図 L13-23 の単一トリガに統一（案A・FND-106・2026-06-23）。bump 非依存の辺残留検査（RULE-030/001/002/022）のすり抜けを解消。段階0 fail-close・段階④ phase-gate は例外で据置。05-verification.md §2 統一トリガ注記＋段階①②③′トリガ書換（反映済）・config.yaml 不変・`edges: []` |
| DD-20 | ✅ 反映済 | O-1/O-2 の生成元辺を親 P-4 からリーフ P-4-3 へ精緻化（案A・Q-3 から昇格・2026-06-24）。O 型生成元辺粒度をリーフ基準（O-3→P-7-2・O-6→P-4-4）で統一。O-1/O-2 v0.3（→P-4-3・→DD-20 backref）・Q-3 closed・`edges: []` |
| DD-21 | ✅ 反映済 | resolved-FND 辺逆転/backref 付与は **z バンプ**に確定（案A・Q-5 から昇格・2026-06-28・選択肢D 却下）。A-1 の 75 FND を MINOR バンプした誤りを z へ再訂正し新規 101 件 backref ドリフトを解消。SPEC-9（RULE-004）・DD-8 は不変＝DD-8 §4「backref 追加＝z」の適用徹底。`edges: []` |
| DD-22 | ✅ 反映済 | skill の設計層モデリング拡張を確定（Q-6 から昇格・2026-07-01）。**①-C ハイブリッド**（対話入口=skill／非対話 fan-out=orchestrator agent・5段ネスト前提は公式ドキュメントで確認済）＋**②-A（PROMPT 型流用・新要件軸）**（skill を PROMPT 設計ノード化・新 FR＋傘 SPEC で著作エージェント軸 SPEC-27/FR-13 と区別・対象 skill 13件）。後続著作＝新 FR/傘 SPEC・PROMPT-8〜（13件）・`.claude/` fan-out 実装。`edges: []`（被参照＝Q-6→DD-22 昇格辺） |
| Q-1 | ✅ closed | DD-2 へ昇格済み |
| Q-2 | ⏳ open | 傘 SPEC 細分化要否＋ SPEC-29-1/29-2 リーフマップ。推奨 A（傘維持）。オーナー判断待ち |
| Q-3 | ✅ closed | DD-20 へ昇格済み（2026-06-24・選択肢A 採用）。O-1/O-2 生成元辺を P-4-3 へ精緻化 |
| Q-4 | ✅ closed | DD-16 へ昇格済み（2026-06-21・選択肢A 採用） |
| Q-5 | ✅ closed | DD-21 へ昇格（2026-06-28・選択肢A 採用／D 却下）。resolved-FND 辺逆転/backref は z バンプ。A-1 の 101 件新規ドリフトを z 訂正で解消。義務辺 →FND-101/→SPEC-9/→DD-8/→DD-21 |
| Q-6 | ✅ closed | DD-22 へ昇格（2026-07-01・①-C／②-A 採用）。サブ決定確定＝ノード型 PROMPT 流用・対象 skill 13件（価値実現直結）・sprint-1・5段ネスト公式確認済。旧 affects 9辺を →DD-22 昇格辺へ置換・v0.2.0。明細＝DD-22 |
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
- **RULE 定義**: [`docs/doc-system/05-verification.md`](../../../docs/doc-system/05-verification.md) — RULE-001〜031 の完全定義
- **記法ガイド**: [`docs/doc-system/04-notation.md`](../../../docs/doc-system/04-notation.md) — ノード埋め込み・summary バッジ（ノードバージョン x.y）・YAML ブロック形式
