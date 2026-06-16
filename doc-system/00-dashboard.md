# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> **状態と優先度の要約**に絞る——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は要約のみ。**全件列挙はしない**。
>
> **最終更新**: 2026-06-16 ｜ **current_stage**: `analysis`（`docs/doc-system/config.yaml`）
> 直近: **分析層 全面的見直し（DD-12）**。D-3/D-4 のスタンプ結合を解消し D-9〜D-22 へ分割、P-1〜P-7 をリーフ単一動詞へ分解、発火制御を P-2-5 に一元化、I-1-1/1-2/1-3 を退役（D-18/D-19 吸収）。FND-93/94 resolved・Q-2（傘 SPEC 細分化）open。00-dfd.md を L0–L3 で全面再生成。spec-inspector 点検クリーン（dangling 0・ドリフト 0・孤立 0）。

---

## 🔄 直近の作業

| 作業 | 種別 | 状態 |
|---|---|---|
| 分析層 全面的見直し：D 分割・P リーフ分解・P-2-5 新設・I-1-x 退役・DFD 再生成（DD-12） | DD-12 | ✅ reflected（2026-06-16）。Pass1〜3b で段階反映。FND-93/94 resolved・Q-2 open。spec-inspector クリーン |
| PR #27 レビュー対応：終了コードの O モデル化（③）・PR 説明是正（②） | FND ×1 | ✅ resolved（2026-06-16）。O-6「終了コード」新設で P-4-4 終端出力を価値経路接続（FND-95）。DFD/ダッシュボード反映 |
| current_stage を `analysis` へ進行（N1） | N | ✅ done（2026-06-15）。config.yaml 更新・stage 進行後 spec-inspector 点検クリーン |
| 依存グラフ機能の分析層補完 O-4/O-5/P-8/P-9（N8） | DD-6 | ✅ reflected（2026-06-15）。analysis-author 著作→reconciliation 反映。E-1 整合不整合は FND-92 で resolved。DD-6 反映完了 |
| E-1 本文が P-8/P-9・O-4/O-5 を未反映の不整合（FND-92） | FND ×1 | ✅ resolved（2026-06-15）。E-1 本文改訂（`--coverage`/P-3-2 先例と整合・新 E 不要）。z バンプ据置（DD-8 §4）|
| PEND 義務辺残存 failure SPEC 新設（FND-80） | FND ×1 | ✅ resolved（2026-06-15）。SPEC-55（RULE-022 WARNING）新設で decision_spine 3型カバレッジ対称回復 |
| 自己点検残課題 FND-85/86/87/90 を即処置（DD-11 新設） | FND ×4 | ✅ resolved（2026-06-15）。SPEC-49 用語訂正／`{NFR-id}-check` 台帳登録／SPEC-30 D カバレッジ明記／SPEC-45・46 観測主体一意化 |
| 全 SPEC 自己点検（spec-inspector ×6・175 ノード） | 点検 | ✅ 構造クリーン。2-object 子2件を即修正（SPEC-29-2／SPEC-31-1 分割）・新規残課題を FND-85〜91 起票（2026-06-15） |
| 03-spec.md 本文品質（FND-40〜77）テスタブル化分割 | FND ×38 | ✅ resolved（2026-06-15） |

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | 備考 |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 210 | ✅ 著作・点検済 | VERIFY-2/5。本文品質 FND-40〜77 をテスタブル化分割（SPEC 子展開で 174 ノード・うち post-mvp 24） |
| analysis | ACTOR / I / O / D / P / E | 92 | ✅ **current stage**・著作/点検済 | DD-12 全面見直し：D-9〜D-22 分割（+14）・P-1〜P-7 全リーフ分解（+39）・P-2-5 新設・I-1-1/1-2/1-3 退役（-3）。O-6 終了コード追加（FND-95・PR#27 ③）。00-dfd.md を L0–L3 で再生成 |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 0 | ⬜ 未着手（次フェーズ） | `/impl-design-pipeline` で着手 |
| implementation | SRC（spec-inspector・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビュー VERIFY-1〜5 は実施済 |
| 横断スパイン | DD / Q / PEND | 17 | ✅ | DD-1〜12（全反映済・DD-12 分析層見直し）・Q-1 closed・Q-2/Q-3 open・PEND-1 resolved・PEND-2 deferred |

> 凡例：✅ 完了／🔄 進行中／⬜ 未着手。ノード数は `-N` 子・`labels: post-mvp` を含む実数。
> current_stage が `analysis` に進行（N1）。analysis 発火の辺ルールは spec-inspector 点検でクリーン確認済み。design 以降の被依存辺ルールは沈黙中（design 着手で発火）。

---

## 🔥 推奨ネクストアクション

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N2 | 設計層（凍結セット）着手 | 🟡 中 | analysis 確定済み。`/impl-design-pipeline`＋design-author で ORC/DS/MOD/… を著作。新規資産前に asset-auditor（A14） |
| N3 | 実装（FR-10：spec-inspector CLI） | 🔵 低 | Python 標準ライブラリのみ・段階①②③。設計確定後 |
| N11 | 03-spec.md 残課題 FND-79/81/82/83/88/89/91（INFO 7件）の実施スプリント決定 | 🔵 低 | 全 INFO・`scheduled` 未設定。オーナー判断待ち（独断繰り越し禁止） |

> **完了済み（経緯は DD/FND ノードに保全・PR8）**: **N1（current_stage→analysis・2026-06-15）／N8（O-4/O-5/P-8/P-9 補完・FND-92・2026-06-15）**／N0（VERIFY-2 再点検）／N4（PEND-1 resolved）／N5（VERIFY-3・P 単一責務）／N6（DD-5・NFR→SPEC 導出）／N7（FND-18・SPEC-52/53・RULE-028）／N9・N10（VAL-5/6・SR-8/9 を sprint-2 起票）／DFD 生成（03-analysis/00-dfd.md）／**分析層全面見直し（DD-12・FND-93/94・I-1-x 退役・DFD 再生成・2026-06-16）**／PR #21・#22 レビュー（FND-24〜39）。

---

## ⏳ オーナー判断待ち

**計 3 件**

| 項目 | 優先 | 種別 | 次アクション |
|---|---|---|---|
| Q-2：傘 SPEC（SPEC-21/25/1・SPEC-29）の細分化要否＋ SPEC-29-1/29-2 リーフマップ | 🟡 中 | Q | 推奨 A（傘マップ維持・実害顕在時に細分化）。方針・実施スプリントはオーナー判断。`scheduled` 未設定 |
| Q-3：O-1/O-2 の生成元辺を P-4-3（リーフ）へ精緻化するか親 P-4 のままか | 🔵 低 | Q | 推奨 A（リーフ先例 O-3/O-6・フロー表に統一・最小変更）。採否・実施スプリントはオーナー判断。`scheduled` 未設定 |
| 03-spec.md 残課題 FND-79・81・82・83・88・89・91（計7件・open） | 🟡 中 | FND | 横断整合＋自己点検残課題の実施スプリント決定（全 INFO）。`scheduled` 未設定 |

> N1（current_stage→analysis）は 2026-06-15 オーナー指示で実施済み。

---

## 📋 FND サマリ

**計 95 件：✅ resolved 87 ／ ⏳ open 8**

> 本文品質 FND-40〜77（38件）は各 SPEC の `期待動作` を「`【条件】のとき、〇〇を▲▲する`」の単一アサーション子 SPEC へ `-N` 分割して全解消。親はアンブレラ化し可視バッジ据置（DD-8 z-bump）・子は親バッジ x.y を ref_version 参照。FND-78（DD-9）・FND-84（DD-10）も resolved。**FND-85〜91** は全 SPEC 自己点検（spec-inspector ×6）で surfaced した残課題（オーナー判断: 全件起票）。うち **FND-80/85/86/87/90 を即処置（resolved・2026-06-15・DD-11 新設・SPEC-55 新設）**。**FND-92**（N8 で顕在化した E-1 本文と P-8/P-9・O-4/O-5 の不整合）も即 resolved（E-1 本文改訂・`--coverage`/P-3-2 先例と整合・新 E 不要・DD-8 §4 z バンプ据置）。**FND-93/94**（分析層全面見直しで顕在化：FND-93＝旧 D-4 の condition/result/log_ref 欠落による価値経路断絶／FND-94＝総点検 G1・G4 の被覆ドリフト）も即 resolved（2026-06-16・DD-12）。**FND-95**（PR #27 レビュー③：P-4-4 終了コードの O/D 未モデル＝PR6 価値経路の穴）も O-6「終了コード」新設で resolved（2026-06-16）。残 open（FND-79/81/82/83/88/89/91）は全て INFO・`scheduled` 未設定。明細は `04-verification/02-findings.md`。

### open 明細（8 件・`scheduled` は未設定でオーナー判断待ち）

| ID | 深刻度 | 状態 | 概要 |
|---|---|---|---|
| FND-35 | WARNING | 🗓 sprint-2（承認済） | config `SPEC→SPEC` OR ループホール（推奨 ②＋③） |
| FND-79 | INFO | ⏳ open | RULE-006/025/026 が複数 SPEC に分散 → 索引化 |
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
| Q-1 | ✅ closed | DD-2 へ昇格済み |
| Q-2 | ⏳ open | 傘 SPEC 細分化要否＋ SPEC-29-1/29-2 リーフマップ。推奨 A（傘維持）。オーナー判断待ち |
| Q-3 | ⏳ open | O-1/O-2 生成元辺の粒度（親 P-4 vs リーフ P-4-3）。推奨 A（P-4-3 へ精緻化）。オーナー判断待ち |
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
