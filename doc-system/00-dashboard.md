# doc-system ダッシュボード

> doc-system（ドッグフーディング・ノードグラフ）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> 議論や著作が進んだらここを更新する。**全件列挙はしない**——明細（FND/SPEC/ノード本体）は各層ファイル、本帳票は**状態と優先度の要約**に絞る。
>
> **最終更新**: 2026-06-13（DD-5（NFR SPEC 必須化・open）・DD-6（依存グラフ機能・open）・FND-18（I/O フォーマット SPEC 欠落）起票）｜ **current_stage**: `requirements`（`docs/doc-system/config.yaml`）

---

## 🔄 現在の作業（2026-06-13 時点）

| 作業 | 種別 | 状態 |
|---|---|---|
| DD-5：NFR から SPEC 導出を必須化（影響範囲調査・ルール/config/Skill 追加） | DD（open） | 🔄 起票済み・NFR-1〜6 への義務辺あり・調査中 |
| DD-6：依存グラフレポート出力＋複雑度算出機能追加（FR-15/16 著作） | DD（open） | 🔄 起票済み・FR 著作待ち |
| FND-18：I/O フォーマット SPEC 欠落の是正（FR-1/FR-11/FR-14 配下 SPEC 追加） | FND（open） | 🔄 起票済み・SPEC 著作待ち |
| N5：P 単一責務違反の点検と修正 | N | ⬜ 未着手 |
| N1：current_stage を analysis へ進める判断 | N | ⬜ 判断待ち |

---

## 📊 ステージ別完成度

| ステージ | 対象型 | ノード | 状態 | レビュー |
|---|---|---|---|---|
| requirements | VAL / SR / FR / NFR / SPEC | 97 | ✅ 著作済み | ✅ N0 再点検済（VERIFY-2・SPEC 品質強化バッチ合格） |
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
| N1 | **current_stage を `analysis` へ進める判断** | 🟡 中 | 分析層ドリフト（FND-17→DD-4 で解消済み）・凍結記録扱い（DD-2 で決定済み）の前提条件が揃った。stage 進行の是非をオーナーが判断 |
| N2 | **設計層（凍結セット）の着手** | 🟡 中 | `/impl-design-pipeline` ＋ design-author で ORC/DS/MOD/DM/PORT/… を著作。spec-inspector の物理設計 |
| N3 | **実装（FR-10：spec-inspector CLI）** | 🔵 低 | Python・標準ライブラリのみ。段階①②③。設計確定後 |
| N4 | **PEND-1 を設計段で再評価** | 🔵 低 | I-2/3/4 過分割（FND-6・INFO）。DM/CFG 設計時にトレードオフ比較 |
| N5 | **P 単一責務違反の点検と修正** | 🟡 中 | P-2/P-3 は FND-2/FND-4 対応で分解済みだが、他の P（P-1/P-4/P-5/P-6/P-7）の単一責務確認が未実施。各プロセスが「単一の責務を1文で記述できるか」を点検し、違反があれば DFD レベリングで分解（PR9）・FND 起票 |
| N6 | **NFR-SPEC 導出ルール整備（DD-5 反映）** | 🔴 高 | NFR-1〜6 全件に SPEC 依存辺ゼロ（FND-18 関連）。config に `must_link_to: NFR→[SPEC]` 追加・各 NFR の SPEC 著作・Skill 更新。DD-5 open（義務辺 → NFR-1〜6） |
| N7 | **I/O フォーマット SPEC 是正（FND-18 解消）** | 🟡 中 | I-1 完全フィールドスキーマ SPEC・O-2 出力フォーマット SPEC・I-7 テンプレートフォーマット SPEC を FR-1/FR-11/FR-14 配下に追加 |
| N8 | **依存グラフレポート機能（DD-6 反映）** | 🔵 低（post-mvp） | FR-15（依存グラフ出力）・FR-16（複雑度算出）を著作。新 O-4/O-5・P-8/P-9 ノード追加。設計フェーズで詳細化 |

> ✅ 完了: N0（SPEC 品質強化分の再点検＝VERIFY-2）／旧 N1（SR-4 の NFR 化 → DD-1 で「SR-2 の重複・削除＋再配線」決定・反映済）／旧 N3（Q-1 → DD-2 昇格・VERIFY suppress[RULE-004]付与）／FND-16（FND-1 dangling ACTOR-3 → P-1 張替）／FND-17（→ DD-4 昇格・分析層ドリフト一括解消）。

---

## ⏳ オーナー判断待ち（サマリ）

**計 3 件**（🔴 高 1 ／ 🟡 中 1 ／ 🔵 低 1）

| 項目 | 優先 | 種別 | 状態 | 次アクション |
|---|---|---|---|---|
| DD-5（NFR SPEC 必須化） | 🔴 高 | DD（open・義務辺あり） | NFR-1〜6 への義務辺・RULE-001 発火中 | N6（影響範囲調査→ルール/SPEC 追加） |
| FND-18（I/O フォーマット SPEC 欠落） | 🟡 中 | FND（open・WARNING） | FR-1/11/14 配下 SPEC 不足 | N7（SPEC 著作） |
| PEND-1（I-2/3/4 過分割） | 🔵 低 | PEND（deferred） | FND-6 INFO・設計段へ先送り | N4（設計段で再評価） |

> **FND サマリ**：計 18 件（✅ resolved 16 ／ ⏳ open 2 ＝ FND-6・FND-18）。FND-18（I/O フォーマット SPEC 欠落）は 2026-06-13 起票。
> **VERIFY サマリ**：VERIFY-1（要件〜分析層・2026-06-11）／VERIFY-2（N0 再点検・2026-06-12）。いずれも suppress[RULE-004] 付与済み（DD-2 決定）。
> **Q サマリ**：Q-1（closed・DD-2 へ昇格済み・2026-06-13）。
> **DD サマリ**：DD-1〜4（決定済・反映済）・DD-5（NFR SPEC 必須化・open・義務辺あり）・DD-6（依存グラフ機能・open）。

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（`trace_scope.exclude` で除外・ノードを持たない要約帳票）。
- ここは**状態と優先度の要約**に絞る。FND/SPEC/論点の明細は各層ファイルを参照（review-system の `docs/dashboard.md` のような全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。
