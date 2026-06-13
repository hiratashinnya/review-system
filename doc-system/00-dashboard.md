# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> 議論や著作が進んだらここを更新する。**全件列挙はしない**——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は**状態と優先度の要約**に絞る。
>
> **最終更新**: 2026-06-13（N9/N10 クローズ・I-2/3/4→I-1-1/I-1-2/I-1-3 改名＋親辺付与・PEND-1 resolved・FND-6 resolved）｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）

---

## 🔄 現在の作業（2026-06-13 時点）

| 作業 | 種別 | 状態 |
|---|---|---|
| DD-6：依存グラフ機能（spec 層完了・分析層（O-4/O-5/P-8/P-9）著作待ち） | DD（decided・分析層 pending） | 🔄 FR-15/16・SPEC-50/51 著作済み |
| N1：current_stage を analysis へ進める判断 | N | ⬜ 判断待ち |

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | レビュー |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 114 | ✅ 著作済み | ✅ N0 再点検済（VERIFY-2）・SPEC-44〜53・SPEC-14-1・FR-15/16 追加（FND-18 再処置・旧 SPEC-41/42/43 は粒度差し戻しで撤去）・VAL-5/6・SR-8/9（N9/N10 由来・`scheduled: sprint-2`・現フェーズ検査沈黙） |
| analysis | ACTOR / I / O / D / P / E | 30 | ✅ 著作済み | ✅ 点検済（DFD 分解・FND 反映済・N5 で P-7→P-7-1/P-7-2 分解） |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 0 | ⬜ 未着手 | — |
| implementation | SRC（spec-inspector 本体・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビューの VERIFY-1/2・FND は実施済 |
| 横断スパイン | DD / Q / PEND | 8 | — | DD-1〜6（決定済・DD-6 は分析層著作のみ残）・PEND-1（先送り）・Q-1（closed） |

> 凡例：✅ 完了 ／ 🟡 進行中 ／ ⬜ 未着手。ノード数は概算（`labels: post-mvp` を含む）。
> 注：current_stage が `requirements` のため、analysis 以降の被依存辺ルール等は沈黙中（著作は先行済み）。

---

## 🔥 推奨ネクストアクション（優先度付き）

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N1 | **current_stage を `analysis` へ進める判断** | 🟡 中 | 分析層ドリフト（FND-17→DD-4 で解消済み）・凍結記録扱い（DD-2 で決定済み）の前提条件が揃った。stage 進行の是否をオーナーが判断 |
| N8 | **依存グラフ分析層補完著作（O-4/O-5/P-8/P-9）** | 🟡 中 | N1 で stage → analysis に進むと分析層ノード欠落が RULE ドリフトで検出される。O-4/O-5 著作は N1 の直後に即実施。P-8/P-9 は分析層スケルトン → 設計段で詳細化 |
| N2 | **設計層（凍結セット）の着手** | 🟡 中 | `/impl-design-pipeline` ＋ design-author で ORC/DS/MOD/DM/PORT/… を著作。spec-inspector の物理設計 |
| N3 | **実装（FR-10：spec-inspector CLI）** | 🔵 低 | Python・標準ライブラリのみ。段階①②③。設計確定後 |

> ✅ 完了: N0（SPEC 品質強化分の再点検＝VERIFY-2）／旧 N1（SR-4 の NFR 化 → DD-1 で「SR-2 の重複・削除＋再配線」決定・反映済）／旧 N3（Q-1 → DD-2 昇格・VERIFY suppress[RULE-004]付与）／FND-16（FND-1 dangling ACTOR-3 → P-1 張替）／FND-17（→ DD-4 昇格・分析層ドリフト一括解消）／N6（DD-5 decided・SPEC-44〜49 著作・config NFR→[SPEC] 追加）／DD-6 spec 層（FR-15/16・SPEC-50/51 著作）／N7（FND-18 resolved・重複不可方針で再処置＝SPEC-52/53・SPEC-14-1 著作＋RULE-028 追加・初回 SPEC-41〜43 は粒度差し戻しで撤去）／N5（P 単一責務点検＝VERIFY-3・FND-19 で P-7→P-7-1/P-7-2 分解・FND-20 で P-1 にパース段検証 SPEC 接続・P-4/P-5/P-6 は PASS）／分析層 DFD 生成（03-analysis/00-dfd.md・Level 0 コンテキスト図・Level 1 プロセス全体図・Level 2 P-2/P-3/P-7 分解・データフロー一覧）／**N9/N10 クローズ**（図生成＝VAL-5←SR-8・逆起こし＝VAL-6←SR-9 を `scheduled: sprint-2` で起票。FR/SPEC 以降は sprint-2 の実作業へ繰り越し）／**N4 クローズ（PEND-1 resolved）**（I-2/3/4 を I-1-1/I-1-2/I-1-3 に改名・親辺 `to: I-1` 付与・FND-6 resolved）。

---

## ⏳ オーナー判断待ち（サマリ）

**計 0 件**

| 項目 | 優先 | 種別 | 状態 | 次アクション |
|---|---|---|---|---|
| PEND-1（I-1-1/I-1-2/I-1-3 過分割） | — | PEND（**resolved**） | 子ノード改名＋親辺付与で解消・FND-6 resolved | ✅ クローズ（N4） |

> **FND サマリ**：計 20 件（✅ resolved 20 ／ ⏳ open 0）。FND-6（I-1-1/I-1-2/I-1-3 過分割・INFO）は子ノード改名で 2026-06-13 resolved。FND-19（P-7 単一責務違反→P-7-1/P-7-2 分解）・FND-20（P-1 パース段検証 SPEC 無主→接続）は N5 で resolved。FND-18（I/O フォーマット SPEC）も重複不可方針で再処置・resolved。
> **VERIFY サマリ**：VERIFY-1（要件〜分析層・2026-06-11）／VERIFY-2（N0 再点検・2026-06-12）／VERIFY-3（N5・P 単一責務点検・2026-06-13）。いずれも suppress[RULE-004] 付与済み（DD-2 決定）。
> **Q サマリ**：Q-1（closed・DD-2 へ昇格済み・2026-06-13）。
> **DD サマリ**：DD-1〜5（決定済・反映済）・DD-6（decided・spec 層完了・分析層著作待ち）。

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- ここは**状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（review-system の `docs/dashboard.md` のような全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。

## 参考ドキュメント
- **グローバル設定**: [`docs/doc-system/config.yaml`](../../../docs/doc-system/config.yaml) — 必須接続ルール・ステージ・condition 語彙・カバレッジ要件
- **RULE 定義**: [`docs/doc-system/05-verification.md`](../../../docs/doc-system/05-verification.md) — RULE-001〜027 の完全定義
- **記法ガイド**: [`docs/doc-system/04-notation.md`](../../../docs/doc-system/04-notation.md) — ノード埋め込み・YAML フロントマター形式
