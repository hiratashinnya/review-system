# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> 議論や著作が進んだらここを更新する。**全件列挙はしない**——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は**状態と優先度の要約**に絞る。
>
> **最終更新**: 2026-06-12（**N0 完了**：SPEC 品質強化分を再点検＝VERIFY-2 記録・重点バッチ合格。全グラフ走査の副次発見 FND-16〔ERROR〕/FND-17〔WARNING〕/Q-1 を起票）｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | レビュー |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 97 | ✅ 著作済み | ✅ N0 再点検済（VERIFY-2・SPEC 品質強化バッチ合格） |
| analysis | ACTOR / I / O / D / P / E | 28 | ✅ 著作済み | ✅ 点検済（DFD 分解・FND 反映済） |
| design | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT / TERM | 0 | ⬜ 未着手 | — |
| implementation | SRC（spec-inspector 本体・Python CLI） | 0 | ⬜ 未着手 | — |
| verification | TD / TC / TR | 0 | ⬜ 未着手 | 文書レビューの VERIFY-1/2・FND は実施済 |
| 横断スパイン | DD / Q / PEND | 3 | — | DD-1（決定済）・PEND-1（先送り）・Q-1（凍結記録ドリフト・未決） |

> 凡例：✅ 完了 ／ 🟡 進行中 ／ ⬜ 未着手。ノード数は概算（`labels: post-mvp` を含む）。
> 注：current_stage が `requirements` のため、analysis 以降の被依存辺ルール等は沈黙中（著作は先行済み）。

---

## 🔥 推奨ネクストアクション（優先度付き）

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N1 | **FND-16 の処置方針を決める（ERROR・always_error）** | 🔴 高 | FND-1 の `to: ACTOR-3` が削除済みノードを指し RULE-007 発火。推奨＝forward 辺を P-1 へ張替＋P-1→FND-1 付与。要オーナー判断（暫定で張替えない） |
| N2 | **current_stage を `analysis` へ進める判断＋ドリフト一括解消（FND-17）** | 🟡 中 | actors 0.2→0.3 流入辺・VERIFY-1/解消済 FND/PEND の ref_version ドリフト群を analysis 段で一括解消。Q-1 の決定（凍結記録の扱い）に依存 |
| N3 | **Q-1 を決定（凍結記録の RULE-004 ドリフト扱い）** | 🟡 中 | VERIFY/解消済 FND の ref_version を 免除A/都度更新B/再検証シグナルC のいずれにするか。推奨 A。決定後 DD 昇格 |
| N4 | **設計層（凍結セット）の着手** | 🟡 中 | `/impl-design-pipeline` ＋ design-author で ORC/DS/MOD/DM/PORT/… を著作。spec-inspector の物理設計 |
| N5 | **実装（FR-10：spec-inspector CLI）** | 🔵 低 | Python・標準ライブラリのみ。段階①②③。設計確定後 |
| N6 | **PEND-1 を設計段で再評価** | 🔵 低 | I-2/3/4 過分割（FND-6・INFO）。DM/CFG 設計時にトレードオフ比較 |

> ✅ 完了: N0（SPEC 品質強化分の再点検＝VERIFY-2）／旧 N1（SR-4 の NFR 化 → DD-1 で「SR-2 の重複・削除＋再配線」決定・反映済）。

---

## ⏳ オーナー判断待ち（サマリ）

**計 4 件**（🔴 高 1 ／ 🟡 中 2 ／ 🔵 低 1）※ FND-16 は always_error（ブロッカー級）

| 項目 | 優先 | 種別 | 状態 | 次アクション |
|---|---|---|---|---|
| FND-16（FND-1→ACTOR-3 dangling） | 🔴 高 | FND（open・ERROR） | RULE-007 always_error・推奨＝P-1 へ張替 | N1（処置方針を決定） |
| Q-1（凍結記録のドリフト扱い） | 🟡 中 | Q（open） | 推奨 A（RULE-004 免除）・決定で DD 昇格 | N3（決定） |
| FND-17（分析層 ref_version ドリフト群） | 🟡 中 | FND（open・WARNING） | Q-1 決定後に analysis 段で一括解消 | N2（stage 進行時） |
| PEND-1（I-2/3/4 過分割） | 🔵 低 | PEND（deferred） | FND-6 INFO・設計段へ先送り | N6（設計段で再評価） |

> **FND サマリ**：計 17 件（✅ resolved 14 ／ ⏳ open 3 ＝ FND-6・FND-16・FND-17）。FND-7〜11 は分析層 I/O 台帳修正、FND-12〜15 は SPEC 品質強化、**FND-16/17 は N0 全グラフ走査の副次発見**（FND-1 dangling・分析層 ref_version ドリフト群）＝2026-06-12 起票・open。
> **VERIFY サマリ**：VERIFY-1（要件〜分析層・2026-06-11）／**VERIFY-2（N0 再点検・2026-06-12・重点バッチ合格＋副次発見3件）**。
> **Q サマリ**：Q-1（凍結記録の RULE-004 ドリフト扱い・open・推奨 A）。
> **DD サマリ**：DD-1（SR-4 削除・再配線）＝決定済・反映済（義務辺なし・FR-1/9・NFR-1/2/6 が `→DD-1` で被参照）。

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- ここは**状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（review-system の `docs/dashboard.md` のような全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。
