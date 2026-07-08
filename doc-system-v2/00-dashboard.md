# doc-system-v2 ダッシュボード

> doc-system-v2（ドッグフーディング・ノードグラフ v2）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> **状態と優先度の要約**に絞る——明細（ノード本体・辺）は各ノードファイル（`nodes/**/{slug}.md`＋`{slug}.yaml`）、
> 本帳票は要約のみ。**全件列挙はしない**。
>
> **最終更新**: 2026-07-08 ｜ **current_stage**: `design`（`docs/doc-system/config.yaml`）
> 本帳票は **v1 の `doc-system/00-dashboard.md` の後継**（issue #76・v1→v2 cutover）。v1 は
> `doc-system-v1-archive/`（旧 `doc-system/`・`git mv` で履歴保持）へ retire 済み。**正本は本コーパス
> （`doc-system-v2/nodes/**`）**。旧ダッシュボードの経緯・完了ログは archive 側に保全されている
> （消さない＝PR8。参照する場合は `doc-system-v1-archive/00-dashboard.md`）。

---

## 🔄 直近の作業

| 作業 | 種別 | 状態 |
|---|---|---|
| Phase 1 — 安全機構・PROMPT coverage・dashboard 同期 | 実装＋検証＋運用要約更新 | ✅ 完了（2026-07-08）。#129 は PR #133 で `agent-command-gate.sh` の fail-open / false negative / false positive を修正し、review 指摘（`gh --repo/-R pr merge`）も同 PR 内で解消後に merge。#112 は PR #134 で `docidx` PROMPT ノードを追加し、SPEC-61 系本文の 13→14 件不整合も review 指摘後に解消。#114 は PR #135 で `prompt_coverage_targets` を `config.yml` 直読みへ変更。#115 は PR #136 で RULE-032 の PROMPT coverage 判定を `carrier: skill|agent` に拡張し、agent carrier 化による誤欠落を防止。実測は 598 ノード、drift 0 件、PROMPT coverage 欠落 0 件。 |
| issue #118 — suppress 機構の廃止（凍結の発想自体を撤去） | 機構廃止（コード＋要件層＋検証層） | ✅ 完了（2026-07-07）。オーナー方針「drift(RULE-004) は凍結免除せず無条件発火させ、依存先更新時の影響確認を必須化する」に基づき suppress/suppress_reason 機構自体を撤去。コード側：`schema/sidecar.schema.json`・`validate.py`・`dsv2/query.py`（`_suppresses_drift()` 撤去）・`dsv2/meta.py`・`dsv2/viewer.py`・`config.yml`（`always_error:` 撤去・dead code 確認済み）から suppress を除去し FORMAT.md/notation.md を追随。コーパス側：FR「三軸の検査抑制機構」を二軸に改訂＋axis③（suppress）子孫 SPEC 6件を退役表記、VERIFY 5件から suppress 除去＋凍結機構固有辺を本文 out-of-graph 記録へ退避、FR 5件（RULE-018 用）の suppress を本文プロースへ移行。DD-2（VERIFY の RULE-004 免除決定）を新規 DD で明示的に破棄。ドリフト resync 28件（本バッチの版上げ由来分含む）を機械的に解消（drift 0 件）。分析/設計層（P-2-5/D-4/D-12/D-18/P-7・DM-1/MOD-filter）の未追随は新規 open FND で別途フラグ（本 PR スコープ外・オーナー判断待ち）。 |
| issue #76 — doc-system v1→v2 フォーマット根本刷新 | tracking issue（Sub-A〜F：#70-75）＋本 cutover | ✅ 完了（2026-07-05）。①本文/メタ属性分離（`{slug}.md`＋`{slug}.yaml`）②連番 id 廃止（slug=正規化タイトル・path 非依存）③1ファイル1ノード化を実施。Sub-A（新フォーマット確定・#70）→Sub-B（585 ノード一括移行・#71）→Sub-C（ツール刷新・#72）→Sub-D（著作パイプライン更新・#73）→Sub-E（テンプレート改訂・#74）→Sub-F（doc_view.html 生成器・#75）が全完了済み。本セッションで**最終カットオーバー**を実施：v1 `doc-system/` を `doc-system-v1-archive/` へ retire（`git mv`）、v1 専用 `backref/` を `archive/backref-v1/` へ retire、`docidx/` は v1-legacy-only である旨を README に明記（`nodeyaml.py` は v2 `dsv2`/`doc-system-v2/validate.py` の共有インフラとして存続）、`docidx-lookup` サブエージェントを dsv2-native（`python3 -m dsv2 index`＋grep/Read）に書き換え、`CLAUDE.md`／`.github/copilot-instructions.md` の正本ポインタを `doc-system/` → `doc-system-v2/` へ全面更新。 |

> 完了済みの旧作業（v1 時代・〜2026-07-04）は `doc-system-v1-archive/00-dashboard.md` に保全（消さない＝PR8）。

---

## 📊 ステージ別ノード数（v2 実測）

| ステージ | ディレクトリ | ノード数（`.yaml`） | 主な型 |
|---|---|---|---|
| 01-why | `nodes/01-why/` | 14 | VAL / SR |
| 02-what | `nodes/02-what/` | 253 | FR / NFR / SPEC |
| 03-analysis | `nodes/03-analysis/` | 98 | ACTOR / I / O / D / P / E / TERM |
| 04-verification | `nodes/04-verification/` | 156 | TD / TC / TR / VERIFY / FND / DD / Q / PEND |
| 05-design | `nodes/05-design/` | 77 | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT |
| **計** | `nodes/**` | **598** | v1 移行後の増分著作を含む現行実測 |

> ノード数は `python3 -m dsv2 index --root doc-system-v2` の 2026-07-08 実測。`doc-system-v2/meta.json`
> が古い場合、照会系コマンドは古い集計を読むため、最新値確認前に `index` を再生成する。
> 2026-07-08 時点では `python3 -m dsv2 drift --root doc-system-v2` は drift 0 件、
> `python3 -m dsv2 prompt-coverage --root doc-system-v2` は PROMPT coverage 欠落 0 件。

---

## ⏳ オーナー判断待ち（open FND / Q / PEND 要約）

**計 14 件**（open FND 12・open Q 1・deferred PEND 1）。明細は各ノードファイル（`nodes/04-verification/{fnd,q,pend}/**`）を参照。

### open FND（12 件）

| タイトル（要約） | scheduled | 備考 |
|---|---|---|
| config の `SPEC→[FR, NFR, SPEC]` OR 規則のループホール | 🗓 sprint-2（承認済） | v1 時代の FND-35 相当。オーナー承認済み |
| `backref check` の open-but-backref 判定がトートロジーで open FND を全件誤検出（issue #64 Category A） | 未設定 | out-of-graph（`archive/backref-v1/` 内）のバグ記録。v1 archive 化により実害は収束 |
| RULE-006/025/026 が複数 SPEC に分散し全体把握の負荷 | 未設定 | 索引化検討 |
| SPEC-9-1 と SPEC-10 が同一 RULE-004 検出でほぼ同主張 | 未設定 | 統合検討 |
| always_error 系 SPEC の condition が不揃い（SPEC-6=error, SPEC-7=failure） | 未設定 | condition 語彙の不揃い |
| SPEC-13 の期待動作が条件節文頭のテスタブル様式に整っていない | 未設定 | 文言整形 |
| 傘 SPEC の condition が子の condition 多様性を代表せずミスリード | 未設定 | 傘 SPEC 表記の精度 |
| SPEC-3-1 が人手の ID 採番行為を期待動作とし機械観測が難しい＋例の欠落 | 未設定 | テスタブル化検討 |
| SPEC-31 の親が FR-1 だが trace_scope 主題の FR-9 が自然 | 未設定 | 親辺の妥当性再検討 |
| `_drift` が x.y.z フル比較で z バンプを誤ドリフト検出する（spec↔impl 乖離） | 未設定 | 実装時に要検証 |
| 設計接続規則の決定（FND-96・DD-15）が out-of-graph 著作資産に未伝播 | 未設定 | 著作資産側への反映漏れ点検 |
| 分析・設計層が三軸抑制モデルのまま issue #118 の suppress 廃止に未追随（P-2-5/D-4/D-12/D-18/P-7・DM-1/MOD-filter） | 未設定 | issue #118 で要件層（FR「三軸→二軸」）・検証層（VERIFY 5件）・コード（dsv2）は追随済みだが、分析層 DFD・設計層 DM-1/MOD が旧三軸モデルのまま。DFD 再分解・型仕様の作り替えは後続設計タスク。実施スプリントはオーナー判断 |

> 全て `scheduled` 未設定（オーナー判断待ち。1件のみ sprint-2 承認済み）は**独断で繰り越さない**
> （CLAUDE.md「スケジュール独断禁止」）。

### open Q（1 件）

| タイトル（要約） | 備考 |
|---|---|
| リーフプロセスの SPEC 1:1 不足（傘 SPEC 暫定マップ）— 要件層で SPEC を細分化するか傘マップ維持か | v1 時代の Q-2 相当。推奨＝傘マップ維持（実害顕在時に細分化）。方針・実施スプリントはオーナー判断 |

### deferred PEND（1 件）

| タイトル（要約） | 備考 |
|---|---|
| 分析層の図（コンテキスト図・DFD）の手動メンテをスクリプト自動生成へ置換 | sprint-2 以降で検討（VAL-5/FR-15） |

---

## 🔥 推奨ネクストアクション

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N1 | 実装（FR-10：spec-inspector CLI） | 🔵 低 | Python 標準ライブラリのみ。凍結セット確定後 |
| N2 | テスト戦略④（凍結セット残項目） | 🟡 中 | 設計層著作済み。`/test-strategy` スキルで TD/TC 設計 |
| N3 | ダッシュボード（open Q/FND/DD 等）の自動集計サブコマンド | 🔵 低 | 本ダッシュボードは手動著作の暫定版。`dsv2` に集計サブコマンドを追加する構想は [issue #108](https://github.com/hiratashinnya/review-system/issues/108) へ切り出し済み。Phase 1 では手動同期のみ完了 |
| N4 | open FND 12件・open Q 1件の実施スプリント決定 | 🟡 中 | 全件 `scheduled` 未設定（1件を除く）。オーナー判断待ち（独断繰り越し禁止） |

---

## 今後（自動化の別 issue）

本ダッシュボードは**手で書いた最小版**（オーナー方針・2026-07-05）。open FND/Q/DD を `doc-system-v2/nodes/04-verification/**` から自動集計し本ファイルを生成する `dsv2` サブコマンドの追加は、本カットオーバーとは別スコープとして [issue #108](https://github.com/hiratashinnya/review-system/issues/108) へ切り出した。

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（ノードを持たない要約帳票。`docs/doc-system/config.yaml` の `trace_scope.exclude` 対象は v1 パスのみだが、本ファイルは `doc-system-v2/` 直下でノード対象ディレクトリ `nodes/**` の外にあるため元々対象外）。
- **状態と優先度の要約**に絞る。FND/Q/DD の明細は各ノードファイルを参照（全件列挙はしない）。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。

## 参考ドキュメント
- **新フォーマット定義**: [`doc-system-v2/FORMAT.md`](FORMAT.md) — 1ファイル1ノード・slug id・サイドカー schema
- **記法ガイド**: [`doc-system-v2/notation.md`](notation.md)
- **グローバル設定**: [`doc-system-v2/config.yml`](config.yml) — 必須接続ルール・ステージ・condition 語彙・カバレッジ要件
- **移行レポート**: [`doc-system-v2/MIGRATION_REPORT.md`](MIGRATION_REPORT.md) — v1→v2 一括移行（Sub-B）の全ノード対応表
- **v1 旧ダッシュボード（archive）**: [`doc-system-v1-archive/00-dashboard.md`](../doc-system-v1-archive/00-dashboard.md) — cutover 前の完了ログ・経緯（消さない＝PR8）
