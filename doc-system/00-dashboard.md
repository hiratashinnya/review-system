# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> **状態と優先度の要約**に絞る——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は要約のみ。**全件列挙はしない**。
>
> **最終更新**: 2026-06-15 ｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）
> 直近: 03-spec.md 本文品質 FND-40〜77（38件）をテスタブル化分割で全解消（SPEC 174 ノードへ展開）。

---

## 🔄 直近の作業

| 作業 | 種別 | 状態 |
|---|---|---|
| PEND 義務辺残存 failure SPEC 新設（FND-80） | FND ×1 | ✅ resolved（2026-06-15）。SPEC-55（RULE-022 WARNING）新設で decision_spine 3型カバレッジ対称回復 |
| 自己点検残課題 FND-85/86/87/90 を即処置（DD-11 新設） | FND ×4 | ✅ resolved（2026-06-15）。SPEC-49 用語訂正／`{NFR-id}-check` 台帳登録／SPEC-30 D カバレッジ明記／SPEC-45・46 観測主体一意化 |
| 全 SPEC 自己点検（spec-inspector ×6・175 ノード） | 点検 | ✅ 構造クリーン。2-object 子2件を即修正（SPEC-29-2／SPEC-31-1 分割）・新規残課題を FND-85〜91 起票（2026-06-15） |
| 03-spec.md 本文品質（FND-40〜77）テスタブル化分割 | FND ×38 | ✅ resolved（2026-06-15） |
| config phases 整理・RULE-029 新設（FND-78） | DD-9 | ✅ reflected（2026-06-14） |
| SPEC-47/NFR-1 を DD-8 準拠に修正（FND-84） | DD-10 | ✅ reflected（2026-06-14） |
| ノードバージョニング移行・フロントマター全廃（FND-36） | DD-8 | ✅ reflected（2026-06-14） |
| 依存グラフ機能の分析層補完（O-4/O-5/P-8/P-9） | DD-6 | 🔄 著作待ち |
| current_stage を `analysis` へ進める判断（N1） | N | ⬜ 判断待ち |

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | 備考 |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 210 | ✅ 著作・点検済 | VERIFY-2/5。本文品質 FND-40〜77 をテスタブル化分割（SPEC 子展開で 174 ノード・うち post-mvp 24） |
| analysis | ACTOR / I / O / D / P / E | 29 | ✅ 著作・点検済 | DFD 分解・DD-7 改訂（D 起票／ワークフロー並走） |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 0 | ⬜ 未着手 | — |
| implementation | SRC（spec-inspector・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビュー VERIFY-1〜5 は実施済 |
| 横断スパイン | DD / Q / PEND | 13 | 🔄 | DD-1〜10（DD-6 のみ分析層 pending）・Q-1 closed・PEND-1 resolved・PEND-2 deferred |

> 凡例：✅ 完了／🔄 進行中／⬜ 未着手。ノード数は `-N` 子・`labels: post-mvp` を含む実数。
> current_stage が `requirements` のため、analysis 以降の被依存辺ルールは沈黙中（著作は先行済み）。

---

## 🔥 推奨ネクストアクション

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N1 | current_stage を `analysis` へ進める判断 | 🟡 中 | 前提（FND-17→DD-4 ドリフト解消・DD-2 凍結記録）が揃った。stage 進行可否をオーナーが判断（N8 連動） |
| N8 | 依存グラフ分析層補完（O-4/O-5/P-8/P-9） | 🟡 中 | N1 で analysis へ進むと分析層ノード欠落がドリフト検出される。N1 直後に O-4/O-5 著作 |
| N2 | 設計層（凍結セット）着手 | 🟡 中 | `/impl-design-pipeline`＋design-author で ORC/DS/MOD/… を著作 |
| N3 | 実装（FR-10：spec-inspector CLI） | 🔵 低 | Python 標準ライブラリのみ・段階①②③。設計確定後 |

> **完了済み（経緯は DD/FND ノードに保全・PR8）**: N0（VERIFY-2 再点検）／N4（PEND-1 resolved）／N5（VERIFY-3・P 単一責務）／N6（DD-5・NFR→SPEC 導出）／N7（FND-18・SPEC-52/53・RULE-028）／N9・N10（VAL-5/6・SR-8/9 を sprint-2 起票）／DFD 生成（03-analysis/00-dfd.md）／PR #21・#22 レビュー（FND-24〜39）。

---

## ⏳ オーナー判断待ち

**計 2 件**

| 項目 | 優先 | 種別 | 次アクション |
|---|---|---|---|
| N1：current_stage を `analysis` へ | 🟡 中 | N | stage 進行 or 現状維持を決定（N8 連動） |
| 03-spec.md 残課題 FND-79・81・82・83・88・89・91（計7件・open） | 🟡 中 | FND | 横断整合＋自己点検残課題の実施スプリント決定（全 INFO）。`scheduled` 未設定 |

---

## 📋 FND サマリ

**計 91 件：✅ resolved 83 ／ ⏳ open 8**

> 本文品質 FND-40〜77（38件）は各 SPEC の `期待動作` を「`【条件】のとき、〇〇を▲▲する`」の単一アサーション子 SPEC へ `-N` 分割して全解消。親はアンブレラ化し可視バッジ据置（DD-8 z-bump）・子は親バッジ x.y を ref_version 参照。FND-78（DD-9）・FND-84（DD-10）も resolved。**FND-85〜91** は全 SPEC 自己点検（spec-inspector ×6）で surfaced した残課題（オーナー判断: 全件起票）。うち **FND-80/85/86/87/90 を即処置（resolved・2026-06-15・DD-11 新設・SPEC-55 新設）**。残 open（FND-79/81/82/83/88/89/91）は全て INFO・`scheduled` 未設定。明細は `04-verification/02-findings.md`。

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
| DD-6 | 🔄 一部 pending | spec 層完了・分析層（O-4/O-5/P-8/P-9）著作待ち |
| DD-7 | ✅ 反映済 | 分析層 DFD 改訂（D 起票／並走著作／退役 ID 不再利用） |
| DD-8 | ✅ 反映済 | ノードバージョニング正式化・フロントマター全廃・ref_version 一括移行（170 件・ドリフト 0） |
| DD-9 | ✅ 反映済 | config phases から post-mvp 除去・RULE-029 新設（FND-78） |
| DD-10 | ✅ 反映済 | SPEC-47 をノードバッジ x.y 検証に置換・NFR-1/SPEC-44 訂正（FND-84） |
| Q-1 | ✅ closed | DD-2 へ昇格済み |
| PEND-1 | ✅ resolved | 過分割 → 子ノード化（FND-6 resolved） |
| PEND-2 | 🗓 deferred | 図のスクリプト生成は VAL-5/FR-15 で sprint-2 以降 |

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- **状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。

## 参考ドキュメント
- **グローバル設定**: [`docs/doc-system/config.yaml`](../../../docs/doc-system/config.yaml) — 必須接続ルール・ステージ・condition 語彙・カバレッジ要件
- **RULE 定義**: [`docs/doc-system/05-verification.md`](../../../docs/doc-system/05-verification.md) — RULE-001〜029 の完全定義
- **記法ガイド**: [`docs/doc-system/04-notation.md`](../../../docs/doc-system/04-notation.md) — ノード埋め込み・summary バッジ（ノードバージョン x.y）・YAML ブロック形式
