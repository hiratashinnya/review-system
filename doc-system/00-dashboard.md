# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> 議論や著作が進んだらここを更新する。**全件列挙はしない**——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は**状態と優先度の要約**に絞る。
>
> **最終更新**: 2026-06-14（H1/H2/H3 処置完了＝FND-24〜27 resolved：config `SPEC→[FR,NFR,SPEC]` 拡張・trace_scope.exclude に `**/00-dfd.md` 追加・connection-matrix.md v0.2.1 改訂。open 4 件（FND-28/31/32/33）残）｜旧: PR #21 オーナーレビュー VERIFY-4 起票・FND-24〜33 起票・FND-29・FND-30 resolved）｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）

---

## 🔄 現在の作業（2026-06-14 時点）

| 作業 | 種別 | 状態 |
|---|---|---|
| H1/H2/H3 処置（FND-24〜27）| FND resolved | ✅ 完了（2026-06-14） |
| DD-6：依存グラフ機能（spec 層完了・分析層（O-4/O-5/P-8/P-9）著作待ち） | DD（decided・分析層 pending） | 🔄 FR-15/16・SPEC-50/51 著作済み |
| N1：current_stage を analysis へ進める判断 | N | ⬜ 判断待ち |

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | レビュー |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 115 | ✅ 著作済み | ✅ N0 再点検済（VERIFY-2）・SPEC-44〜54・SPEC-14-1・FR-15/16 追加（FND-18 再処置・旧 SPEC-41/42/43 は粒度差し戻しで撤去）・SPEC-54（P-7 記載内容入力・FND-23）・VAL-5/6・SR-8/9（N9/N10 由来・`scheduled: sprint-2`・現フェーズ検査沈黙） |
| analysis | ACTOR / I / O / D / P / E | 37 | ✅ 著作済み | ✅ 点検済（DFD 分解・FND 反映済・N5 で P-7→P-7-1/P-7-2 分解・DFD レビューで D-3〜D-8/I-9 起票＝FND-21/22/23・DD-7） |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 0 | ⬜ 未着手 | — |
| implementation | SRC（spec-inspector 本体・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビューの VERIFY-1/2・FND は実施済 |
| 横断スパイン | DD / Q / PEND | 10 | — | DD-1〜7（決定済・DD-6 は分析層著作のみ残・DD-7 分析層 DFD 改訂）・PEND-1（resolved）・PEND-2（先送り・図のスクリプト生成）・Q-1（closed） |

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

> ✅ 完了: N0（SPEC 品質強化分の再点検＝VERIFY-2）／旧 N1（SR-4 の NFR 化 → DD-1 で「SR-2 の重複・削除＋再配線」決定・反映済）／旧 N3（Q-1 → DD-2 昇格・VERIFY suppress[RULE-004]付与）／FND-16（FND-1 dangling ACTOR-3 → P-1 張替）／FND-17（→ DD-4 昇格・分析層ドリフト一括解消）／N6（DD-5 decided・SPEC-44〜49 著作・config NFR→[SPEC] 追加）／DD-6 spec 層（FR-15/16・SPEC-50/51 著作）／N7（FND-18 resolved・重複不可方針で再処置＝SPEC-52/53・SPEC-14-1 著作＋RULE-028 追加・初回 SPEC-41〜43 は粒度差し戻しで撤去）／N5（P 単一責務点検＝VERIFY-3・FND-19 で P-7→P-7-1/P-7-2 分解・FND-20 で P-1 にパース段検証 SPEC 接続・P-4/P-5/P-6 は PASS）／分析層 DFD 生成（03-analysis/00-dfd.md・Level 0 コンテキスト図・Level 1 プロセス全体図・Level 2 P-2/P-3/P-7 分解・データフロー一覧）／**N9/N10 クローズ**（図生成＝VAL-5←SR-8・逆起こし＝VAL-6←SR-9 を `scheduled: sprint-2` で起票。FR/SPEC 以降は sprint-2 の実作業へ繰り越し）／**N4 クローズ（PEND-1 resolved）**（I-2/3/4 を I-1-1/I-1-2/I-1-3 に改名・親辺 `to: I-1` 付与・FND-6 resolved）／**DFD Level 1 オーナーレビュー処置**（FND-21：P-6 の config 直読み→D-3 経由に是正／FND-22：プロセス間データを D-3〜D-8 として起票＝データディクショナリ完成／FND-23：P-7-1 に I-9 ノード記載内容入力を追加＋SPEC-54 新設／DD-7：分析層ワークフロー改訂（図とノード並走著作・D は分析層起票・退役 ID 不再利用）／PEND-2：図のスクリプト自動生成は VAL-5/FR-15 に統合し sprint-2 へ先送り）／**PR #21 レビュー処置**（VERIFY-4 起票・FND-24〜33 起票（H1/H2/H3/M1〜M4/L1〜L3 計10件）・FND-29（PR 説明文更新）・FND-30（ダッシュボード矛盾修正）は resolved）。

---

## ⏳ オーナー判断待ち（サマリ）

**計 1 件**

| 項目 | 優先 | 種別 | 状態 | 次アクション |
|---|---|---|---|---|
| N1（current_stage を `analysis` へ進める判断） | 🟡 中 | N | ⬜ 判断待ち | オーナーが stage 進行 or 現状維持を決定（N8 も連動） |
| PEND-1（I-1-1/I-1-2/I-1-3 過分割） | — | PEND（**resolved**） | 子ノード改名＋親辺付与で解消・FND-6 resolved | ✅ クローズ（N4） |

### FND サマリ（計 33 件：✅ resolved 29 ／ ⏳ open 4）

PR #21 オーナーレビュー指摘（FND-24〜33・VERIFY-4・2026-06-13）の内訳：

| ID | レベル | 状態 | 概要 |
|---|---|---|---|
| FND-24 | H1（ERROR） | ✅ resolved | SPEC-14-1 RULE-006 違反 → config `SPEC→[FR,NFR,SPEC]` 拡張・spec.md v0.3.6 |
| FND-25 | M1（WARNING） | ✅ resolved | SPEC-48 と config の矛盾 → FND-24 と同根一括解消 |
| FND-26 | H2（ERROR） | ✅ resolved | connection-matrix.md DD-5 未同期 → v0.2.1 に改訂 |
| FND-27 | H3（ERROR） | ✅ resolved | dfd.md out-of-graph 未登録 → trace_scope.exclude に追加 |
| FND-28 | M2（WARNING） | ⏳ open | 追加バッチ（SPEC-44〜54 等）の VERIFY 欠如 |
| FND-29 | M3（WARNING） | ✅ resolved | PR 説明文の乖離 → PR 本文更新済み |
| FND-30 | M4（WARNING） | ✅ resolved | ダッシュボードの判断待ち件数矛盾 → 修正済み |
| FND-31 | L1（INFO） | ⏳ open | DD 影響範囲のバージョン注記が現版と乖離 |
| FND-32 | L2（INFO） | ⏳ open | FR-1 バッジ v0.3 とファイル x.y=0.2 の不一致 |
| FND-33 | L3（INFO） | ⏳ open | tmp 草稿に差し戻し済み SPEC-41〜43 残存 |

> open 4 件（FND-28/31/32/33）は今後着手。FND-1〜23 はすべて resolved（明細は `02-findings.md`）。H1/H2/H3 処置（2026-06-14）で FND-24〜27 を一括 resolved。

### VERIFY サマリ

| ID | 対象 | 実施日 |
|---|---|---|
| VERIFY-1 | 要件〜分析層 | 2026-06-11 |
| VERIFY-2 | N0 再点検 | 2026-06-12 |
| VERIFY-3 | N5・P 単一責務点検 | 2026-06-13 |
| VERIFY-4 | PR #21 オーナーレビュー | 2026-06-13 |

> いずれも suppress[RULE-004] 付与済み（DD-2 決定）。

### DD / Q / PEND サマリ

| ID | 状態 | 概要 |
|---|---|---|
| DD-1〜5 | ✅ 反映済 | 決定済・本文反映完了 |
| DD-6 | 🔄 一部 pending | spec 層完了・分析層（O-4/O-5/P-8/P-9）著作待ち |
| DD-7 | ✅ 反映済 | 分析層 DFD 改訂（D 起票／ワークフロー並走／退役 ID 不再利用） |
| Q-1 | ✅ closed | DD-2 へ昇格済み（2026-06-13） |
| PEND-1 | ✅ resolved | 過分割 → 子ノード化 |
| PEND-2 | ⏳ deferred | 図のスクリプト生成は VAL-5/FR-15 で sprint-2 以降 |

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- ここは**状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（review-system の `docs/dashboard.md` のような全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。

## 参考ドキュメント
- **グローバル設定**: [`docs/doc-system/config.yaml`](../../../docs/doc-system/config.yaml) — 必須接続ルール・ステージ・condition 語彙・カバレッジ要件
- **RULE 定義**: [`docs/doc-system/05-verification.md`](../../../docs/doc-system/05-verification.md) — RULE-001〜027 の完全定義
- **記法ガイド**: [`docs/doc-system/04-notation.md`](../../../docs/doc-system/04-notation.md) — ノード埋め込み・YAML フロントマター形式
