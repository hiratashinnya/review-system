# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> 議論や著作が進んだらここを更新する。**全件列挙はしない**——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は**状態と優先度の要約**に絞る。
>
> **最終更新**: 2026-06-12（N1 完了：SR-4 を SR-2 の重複として削除・再配線＝DD-1）｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | レビュー |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 86 | ✅ 著作済み | ✅ spec-inspector 点検済（FND・DD-1 反映済） |
| analysis | ACTOR / I / O / D / P / E | 29 | ✅ 著作済み | ✅ 点検済（DFD 分解・FND 反映済） |
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

> **FND サマリ**：計 6 件（✅ resolved 5 ／ ⏳ open 1 ＝ FND-6 ＝ PEND-1）。解消済みは処置ノードに `→ FND-x` を付与済み。
> **DD サマリ**：DD-1（SR-4 削除・再配線）＝決定済・反映済（義務辺なし・FR-1/9・NFR-1/2/6 が `→DD-1` で被参照）。

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- ここは**状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（review-system の `docs/dashboard.md` のような全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。
