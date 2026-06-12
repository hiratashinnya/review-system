# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> 議論や著作が進んだらここを更新する。**全件列挙はしない**——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は**状態と優先度の要約**に絞る。
>
> **最終更新**: 2026-06-12（SPEC 品質強化：テスタビリティ基準策定・condition 語彙に `empty` 追加・パース検証 RULE-023〜027 追加・FR-11 改訂＋FR-13/14 新設・SPEC-1/2/26/27 書き直し＋SPEC-31〜40 追加）｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | レビュー |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 97 | ✅ 著作済み | 🟡 SPEC 品質強化を反映（FR-11/13/14・SPEC-31〜40）→ spec-inspector 再点検が必要 |
| analysis | ACTOR / I / O / D / P / E | 28 | ✅ 著作済み | ✅ 点検済（DFD 分解・FND 反映済） |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 0 | ⬜ 未着手 | — |
| implementation | SRC（spec-inspector 本体・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビューの VERIFY-1 / FND は実施済 |
| 横断スパイン | DD / Q / PEND | 2 | — | DD-1（決定済）・PEND-1（先送り） |

> 凡例：✅ 完了 ／ 🟡 進行中 ／ ⬜ 未着手。ノード数は概算（`labels: post-mvp` を含む）。
> 注：current_stage が `requirements` のため、analysis 以降の被依存辺ルール等は沈黙中（著作は先行済み）。

---

## 🔥 推奨ネクストアクション（優先度付き）

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N0 | **spec-inspector で SPEC 品質強化分を再点検** | 🟡 中 | FR-11/13/14・SPEC-31〜40 追加と condition 語彙拡張（empty）後の孤児/穴/分割違反/カバレッジを確認。新規 SPEC の TD 未紐づけは verification 段沈黙中 |
| N1 | **current_stage を `analysis`／`design` へ進める判断** | 🟡 中 | requirements/analysis は著作・点検済。据え置きだと analysis 段ルール（被依存辺等）が沈黙し続ける。進めると整合違反が発火 |
| N2 | **設計層（凍結セット）の着手** | 🟡 中 | `/impl-design-pipeline` ＋ design-author で ORC/DS/MOD/DM/PORT/… を著作。spec-inspector の物理設計 |
| N3 | **実装（FR-10：spec-inspector CLI）** | 🔵 低 | Python・標準ライブラリのみ。段階①②③。設計確定後 |
| N4 | **PEND-1 を設計段で再評価** | 🔵 低 | I-2/3/4 過分割（FND-6・INFO）。DM/CFG 設計時にトレードオフ比較 |

> ✅ 完了（旧 N1）: SR-4 の NFR 化 → **DD-1** で「SR-4 は SR-2 の重複・削除＋再配線」と決定・反映済み。

---

## ⏳ オーナー判断待ち（サマリ）

**計 1 件**（🔴 高 0 ／ 🟡 中 0 ／ 🔵 低 1）※ ブロッカーなし

| 項目 | 優先 | 種別 | 状態 | 次アクション |
|---|---|---|---|---|
| PEND-1（I-2/3/4 過分割） | 🔵 低 | PEND（deferred） | FND-6 INFO・設計段へ先送り | N4（設計段で再評価） |

> **FND サマリ**：計 15 件（✅ resolved 14 ／ ⏳ open 1 ＝ FND-6 ＝ PEND-1）。解消済みは処置ノードに `→ FND-x` を付与済み。FND-7〜11 は分析層 I/O 台帳修正、**FND-12〜15 は SPEC 品質強化**（FR-1 分割不足・condition 語彙 empty 欠落・SPEC 本文の非テスタブル・FR-11 過積載）＝2026-06-12 起票・反映済。
> **DD サマリ**：DD-1（SR-4 削除・再配線）＝決定済・反映済（義務辺なし・FR-1/9・NFR-1/2/6 が `→DD-1` で被参照）。

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- ここは**状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（review-system の `docs/dashboard.md` のような全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。
