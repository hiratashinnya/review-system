# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> 議論や著作が進んだらここを更新する。**全件列挙はしない**——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は**状態と優先度の要約**に絞る。
>
> **最終更新**: 2026-06-13（FND-18 初回処置を粒度差し戻し・SPEC-41/42/43 撤去｜DD-5 decided・DD-6 decided（spec 層）・SPEC-44〜51 著作）｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）

---

## 🔄 現在の作業（2026-06-13 時点）

| 作業 | 種別 | 状態 |
|---|---|---|
| FND-18：I/O フォーマット SPEC（初回処置を差し戻し・テスタブル粒度で再著作） | FND（open・差し戻し） | 🔁 SPEC-41/42/43 撤去済み・1アサーション1SPECで再起票待ち |
| DD-6：依存グラフ機能（spec 層完了・分析層（O-4/O-5/P-8/P-9）著作待ち） | DD（decided・分析層 pending） | 🔄 FR-15/16・SPEC-50/51 著作済み |
| N5：P 単一責務違反の点検と修正 | N | ⬜ 未着手 |
| N1：current_stage を analysis へ進める判断 | N | ⬜ 判断待ち |

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | レビュー |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 107 | ✅ 著作済み | ✅ N0 再点検済（VERIFY-2）・SPEC-44〜51・FR-15/16 追加。SPEC-41/42/43（FND-18）は粒度差し戻しで撤去 |
| analysis | ACTOR / I / O / D / P / E | 28 | ✅ 著作済み | ✅ 点検済（DFD 分解・FND 反映済） |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 0 | ⬜ 未着手 | — |
| implementation | SRC（spec-inspector 本体・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビューの VERIFY-1/2・FND は実施済 |
| 横断スパイン | DD / Q / PEND | 8 | — | DD-1〜4（決定済）・DD-5/6（open）・PEND-1（先送り）・Q-1（closed） |

> 凡例：✅ 完了 ／ 🟡 進行中 ／ ⬜ 未着手。ノード数は概算（`labels: post-mvp` を含む）。
> 注：current_stage が `requirements` のため、analysis 以降の被依存辺ルール等は沈黙中（著作は先行済み）。

---

## 🔥 推奨ネクストアクション（優先度付き）

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N7 | **I/O フォーマット SPEC 再著作（FND-18・差し戻し）** | 🔴 高 | 初回 SPEC-41/42/43 が粒度違反（多アサーション束ね・condition 混在）で差し戻し。1アサーション1SPEC・condition 単位で再起票（I-1 スキーマ→normal/failure 分割・I-7 テンプレ→normal/failure 分割・O-2 は SPEC-29/30 重複点検）。FND-18 本文に再著作プランあり |
| N1 | **current_stage を `analysis` へ進める判断** | 🟡 中 | 分析層ドリフト（FND-17→DD-4 で解消済み）・凍結記録扱い（DD-2 で決定済み）の前提条件が揃った。stage 進行の是否をオーナーが判断 |
| N8 | **依存グラフ分析層補完著作（O-4/O-5/P-8/P-9）** | 🟡 中 | N1 で stage → analysis に進むと分析層ノード欠落が RULE ドリフトで検出される。O-4/O-5 著作は N1 の直後に即実施。P-8/P-9 は分析層スケルトン → 設計段で詳細化 |
| N5 | **P 単一責務違反の点検と修正** | 🟡 中 | P-2/P-3 は FND-2/FND-4 対応で分解済みだが、他の P（P-1/P-4/P-5/P-6/P-7）の単一責務確認が未実施。各プロセスが「単一の責務を1文で記述できるか」を点検し、違反があれば DFD レベリングで分解（PR9）・FND 起票 |
| N2 | **設計層（凍結セット）の着手** | 🟡 中 | `/impl-design-pipeline` ＋ design-author で ORC/DS/MOD/DM/PORT/… を著作。spec-inspector の物理設計 |
| N3 | **実装（FR-10：spec-inspector CLI）** | 🔵 低 | Python・標準ライブラリのみ。段階①②③。設計確定後 |
| N4 | **PEND-1 を設計段で再評価** | 🔵 低 | I-2/3/4 過分割（FND-6・INFO）。DM/CFG 設計時にトレードオフ比較 |

> ✅ 完了: N0（SPEC 品質強化分の再点検＝VERIFY-2）／旧 N1（SR-4 の NFR 化 → DD-1 で「SR-2 の重複・削除＋再配線」決定・反映済）／旧 N3（Q-1 → DD-2 昇格・VERIFY suppress[RULE-004]付与）／FND-16（FND-1 dangling ACTOR-3 → P-1 張替）／FND-17（→ DD-4 昇格・分析層ドリフト一括解消）／N6（DD-5 decided・SPEC-44〜49 著作・config NFR→[SPEC] 追加）／DD-6 spec 層（FR-15/16・SPEC-50/51 著作）。
> ⚠️ N7（FND-18）は初回処置（SPEC-41〜43）が**テスタブル粒度不足で差し戻し**・SPEC 撤去済み・再著作待ち（上表 N7 参照）。

---

## ⏳ オーナー判断待ち（サマリ）

**計 2 件**（🔴 高 1 ／ 🔵 低 1）

| 項目 | 優先 | 種別 | 状態 | 次アクション |
|---|---|---|---|---|
| FND-18（I/O フォーマット SPEC・差し戻し） | 🔴 高 | FND（open・差し戻し） | 初回 SPEC-41/42/43 粒度違反で撤去 | N7（1アサーション1SPECで再著作・O-2 は SPEC-29/30 重複点検） |
| PEND-1（I-2/3/4 過分割） | 🔵 低 | PEND（deferred） | FND-6 INFO・設計段へ先送り | N4（設計段で再評価） |

> **FND サマリ**：計 18 件（✅ resolved 16 ／ ⏳ open 2 ＝ FND-6・FND-18）。FND-18（I/O フォーマット SPEC）は初回処置を 2026-06-13 に粒度差し戻し・再著作待ち。
> **VERIFY サマリ**：VERIFY-1（要件〜分析層・2026-06-11）／VERIFY-2（N0 再点検・2026-06-12）。いずれも suppress[RULE-004] 付与済み（DD-2 決定）。
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
