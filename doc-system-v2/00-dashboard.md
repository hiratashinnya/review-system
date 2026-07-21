# doc-system-v2 ダッシュボード

> doc-system-v2（ドッグフーディング・ノードグラフ v2）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> **状態と優先度の要約**に絞る——明細（ノード属性・辺）は各ノード YAML（`nodes/**/{slug}.yaml`）、
> 本文は型別 body policy に従う Markdown、
> 本帳票は要約のみ。**全件列挙はしない**。
>
> **最終更新**: 2026-07-11 ｜ **current_stage**: `design`（`docs/doc-system/config.yaml`）
> 本帳票は **v1 の `doc-system/00-dashboard.md` の後継**（issue #76・v1→v2 cutover）。v1 は
> `doc-system-v1-archive/`（旧 `doc-system/`・`git mv` で履歴保持）へ retire 済み。**正本は本コーパス
> （`doc-system-v2/nodes/**`）**。旧ダッシュボードの経緯・完了ログは archive 側に保全されている
> （消さない＝PR8。参照する場合は `doc-system-v1-archive/00-dashboard.md`）。

---

## 🔄 直近の作業

| 作業 | 種別 | 状態 |
|---|---|---|
| issue #159 — SPEC 本文系 open FND 解消 | SPEC-3-1/13/9-1+10/31 の文言・親辺・resolved 化 | ✅ 完了（2026-07-11）。対象4件を `fnd/resolved/` へ移動し、処置先 SPEC から backref を付与。 |
| issue #158 — 本文 resolved 済み open FND 整理 | lifecycle 配置整理 | ✅ 完了（2026-07-11）。`_drift` z バンプ誤検出と `backref check` open-but-backref 判定トートロジーの 2 件を、既存 backref と out-of-graph 対象の扱いを確認した上で `fnd/resolved/` へ整理。 |
| issue #152 — scheduled 空欄対策 | 流入防止＋流出検出＋既存空欄整理 | ✅ 完了（2026-07-10）。`scheduled` を非空必須にし、`validate.py` / `schema/sidecar.schema.json` / `dsv2 index` で空欄・欠落を fail-close。移行後追加の空欄 12 件は完了済み/解決済みノードとして `sprint-1` に整理。 |
| issue #161/#163 — 接続規則の価値経路充足性 見直し（Phase A） | ルール監査→DD-9→config反映→in-graphミラー | 🟡 反映済み・施行待ち（2026-07-21）。オーナー確定で **DD-9** を起票し、価値経路の下流連続性規則（p←mod / scm←cfg / ds←prs〔design〕・mod・dm・port・orc・prs・prompt・cfg←src〔impl・シンボル適格性条件付き〕）＋ nfr←spec・spec←td(leaf限定) の error 昇格を `doc-system-v2/config.yml` へ**一括反映**（分割せず）。in-graph は dedicated rule SPEC 10・severity 是正 2・傘改訂・CFG `must_be_linked_from` 同期で追随（618ノード・validate/drift/coverage 全green）。**規則は宣言のみで inert＝施行は #163 Phase B（must_be_linked_from reader 実装）で発火**。Phase A FND は施行完了まで open 維持。SRC シンボル適格性はオーナー再確認待ち（下記 N8）。 |
| issue #157〜#165 — stage completion issue expansion | 進捗管理ファイル更新 | 🟡 一部完了（2026-07-11〜）。#157 Q-2→DD-23、#158/#159 で FND 6 件 resolved。Phase A（#161/#163 規則見直し）反映済み。残りは Phase C open FND 解消（#165/#164）、gate 施行（#163）、SRC/TD/TC/TR materialization（#160/#161・適格性確定後）、`current_stage` advancement（#162）。 |
| issue #142 — docidx archive 判断 | archive 判断＋参照境界更新 | ✅ 完了（2026-07-10）。`docidx/` は物理 archive へ移動しない判断。v1 archive (`doc-system-v1-archive/`) の読み取り CLI として `scan.py`/`cli.py`/`query.py` 等を残し、v2 実行系が import する `docidx.nodeyaml` は共有 YAML reader として存続。現行 v2 の正本照会は `python3 -m dsv2` と通常のファイル検索へ寄せる。**issue #172 で refine**：`nodeyaml.py` のみ `dsv2/nodeyaml.py` へ分離し、残り（`scan.py`/`cli.py`/`query.py`/`render.py`/`model.py`）を `archive/docidx-v1/` へ `git mv`（v1-legacy 誤起動リスクの構造的低減）。 |
| issue #140 — doc_system 用 config 操作エージェント | Codex agent＋repo skill＋PROMPT ノード | ✅ 完了（2026-07-10）。`doc-system-config-operator` と `doc-system-config` skill を追加し、`doc-system-v2/config.yml` の作成・解説・変更時に FORMAT/config/schema/dsv2 と対応 SPEC/SCM/CFG/PROMPT ノードを照合する手順を明文化。PROMPT ノードで agent carrier を在グラフ化。review_system 側の横展開は issue #141 に残す。 |
| 識別子単位ノード・型別本文ポリシーの整理 | DD 起票＋FORMAT/dsv2 土台反映＋authoring 追随 | ✅ FORMAT/dsv2 body policy 反映済み（2026-07-09）。DD「識別子単位ノードは1ノード1YAMLを維持し本文は型別ポリシーで省略・共有を許可する」を追加後、`config.yml: body_policy`、`body_ref.file`/`body_ref.anchor`、YAML 走査 validator、bodyless/shared-body 対応 meta/rename/viewer を反映。PR #147 で SRC layout/schema/存在検査と TD shared body・TC bodyless・TD-TC 1:1 の実装設計・検証規則化を反映。本PRで著作テンプレート/プロンプト追随 FND を resolved 化し、TD/TC/SRC テンプレート、test-strategy、verification-author、共通 authoring/reconciliation 資産を body policy 前提へ同期。実測は 603 ノード、validate エラー 0 件、drift 0 件。 |
| issue #94 — 既存585ノードの scheduled backfill | コーパス機械 backfill＋運用要約更新 | ✅ 完了（2026-07-10）。v1→v2 移行レポートの 585 slug を対象に、空 `scheduled` 558 件を `sprint-1` へ backfill。既存値あり 27 件（`sprint-2` 25 件・`post-mvp` 2 件）と移行後追加 18 件は #94 対象外として保持。 |
| Phase 2 — condition / 傘 SPEC / suppress 廃止後続の同期 | コーパス追随＋検証＋運用要約更新 | ✅ 完了（2026-07-09）。#107 は PR #138 で author update slug reporting を正式化し、著作更新時の slug 報告規約を明確化。#78 は PR #139 で condition follow-up を反映し、condition 語彙・傘 SPEC 周辺の後続整理を完了。suppress 廃止後続 FND は PR #143 で分析/設計層未追随を解消し、issue #118 で残っていた「三軸抑制モデル」表現を Phase 2 として resolved 化。実測は 598 ノード、validate エラー 0 件、drift 0 件、PROMPT coverage 欠落 0 件。 |
| Phase 1 — 安全機構・PROMPT coverage・dashboard 同期 | 実装＋検証＋運用要約更新 | ✅ 完了（2026-07-08）。#129 は PR #133 で `agent-command-gate.sh` の fail-open / false negative / false positive を修正し、review 指摘（`gh --repo/-R pr merge`）も同 PR 内で解消後に merge。#112 は PR #134 で `docidx` PROMPT ノードを追加し、SPEC-61 系本文の 13→14 件不整合も review 指摘後に解消。#114 は PR #135 で `prompt_coverage_targets` を `config.yml` 直読みへ変更。#115 は PR #136 で RULE-032 の PROMPT coverage 判定を `carrier: skill|agent` に拡張し、agent carrier 化による誤欠落を防止。実測は 598 ノード、drift 0 件、PROMPT coverage 欠落 0 件。 |
| issue #118 — suppress 機構の廃止（凍結の発想自体を撤去） | 機構廃止（コード＋要件層＋検証層） | ✅ 完了（2026-07-07）。オーナー方針「drift(RULE-004) は凍結免除せず無条件発火させ、依存先更新時の影響確認を必須化する」に基づき suppress/suppress_reason 機構自体を撤去。コード側：`schema/sidecar.schema.json`・`validate.py`・`dsv2/query.py`（`_suppresses_drift()` 撤去）・`dsv2/meta.py`・`dsv2/viewer.py`・`config.yml`（`always_error:` 撤去・dead code 確認済み）から suppress を除去し FORMAT.md/notation.md を追随。コーパス側：FR「三軸の検査抑制機構」を二軸に改訂＋axis③（suppress）子孫 SPEC 6件を退役表記、VERIFY 5件から suppress 除去＋凍結機構固有辺を本文 out-of-graph 記録へ退避、FR 5件（RULE-018 用）の suppress を本文プロースへ移行。DD-2（VERIFY の RULE-004 免除決定）を新規 DD で明示的に破棄。ドリフト resync 28件（本バッチの版上げ由来分含む）を機械的に解消（drift 0 件）。分析/設計層（P-2-5/D-4/D-12/D-18/P-7・DM-1/MOD-filter）の未追随は Phase 2 / PR #143 で resolved 化済み。 |
| issue #76 — doc-system v1→v2 フォーマット根本刷新 | tracking issue（Sub-A〜F：#70-75）＋本 cutover | ✅ 完了（2026-07-05）。①本文/メタ属性分離（`{slug}.md`＋`{slug}.yaml`）②連番 id 廃止（slug=正規化タイトル・path 非依存）③1ファイル1ノード化を実施。Sub-A（新フォーマット確定・#70）→Sub-B（585 ノード一括移行・#71）→Sub-C（ツール刷新・#72）→Sub-D（著作パイプライン更新・#73）→Sub-E（テンプレート改訂・#74）→Sub-F（doc_view.html 生成器・#75）が全完了済み。本セッションで**最終カットオーバー**を実施：v1 `doc-system/` を `doc-system-v1-archive/` へ retire（`git mv`）、v1 専用 `backref/` を `archive/backref-v1/` へ retire、`docidx/` は v1-legacy-only である旨を README に明記（`nodeyaml.py` は v2 `dsv2`/`doc-system-v2/validate.py` の共有インフラとして存続）、`docidx-lookup` サブエージェントを dsv2-native（`python3 -m dsv2 index`＋grep/Read）に書き換え、`CLAUDE.md`／`.github/copilot-instructions.md` の正本ポインタを `doc-system/` → `doc-system-v2/` へ全面更新。 |

> 完了済みの旧作業（v1 時代・〜2026-07-04）は `doc-system-v1-archive/00-dashboard.md` に保全（消さない＝PR8）。

---

## 📊 ステージ別ノード数（v2 実測）

| ステージ | ディレクトリ | ノード数（`.yaml`） | 主な型 |
|---|---|---|---|
| 01-why | `nodes/01-why/` | 14 | VAL / SR |
| 02-what | `nodes/02-what/` | 253 | FR / NFR / SPEC |
| 03-analysis | `nodes/03-analysis/` | 98 | ACTOR / I / O / D / P / E / TERM |
| 04-verification | `nodes/04-verification/` | 162 | TD / TC / TR / VERIFY / FND / DD / Q / PEND |
| 05-design | `nodes/05-design/` | 78 | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT |
| **計** | `nodes/**` | **605** | v1 移行後の増分著作を含む現行実測 |

> ノード数は `python3 -m dsv2 index --root doc-system-v2` の 2026-07-10 実測。`doc-system-v2/meta.json`
> が古い場合、照会系コマンドは古い集計を読むため、最新値確認前に `index` を再生成する。
> 2026-07-10 時点では `python3 doc-system-v2/validate.py` は validate エラー 0 件、
> `python3 -m dsv2 drift --root doc-system-v2` は drift 0 件、
> `python3 -m dsv2 prompt-coverage --root doc-system-v2` は PROMPT coverage 欠落 0 件。

---

## ⏳ オーナー判断待ち（open FND / Q / PEND 要約）

**計 4 件**（open FND 2・open Q 1・deferred PEND 1）。明細は各ノードファイル（`nodes/04-verification/{fnd,q,pend}/**`）を参照。

### open FND（2 件）

| タイトル（要約） | scheduled | 備考 |
|---|---|---|
| **接続規則が価値経路連続性を error で機械保証していない**（Phase A・#161 本体） | 🗓 sprint-1 | **反映済み・施行待ち（2026-07-21）**。規則セットはオーナー確定→DD-9 で config／in-graph へ反映済み。ただし規則は宣言のみ＝inert で、**機械保証の成立は #163（Phase B）施行器の実装が前提**。施行完了まで open 維持（この FND は「機械保証していない」状態を指すため） |
| config の `SPEC→[FR, NFR, SPEC]` OR 規則のループホール | 🗓 sprint-2（承認済） | v1 時代の FND-35 相当。オーナー承認済み |

> **resolved 済み（2026-07-21・本セッション）**:
> - **FND-99**「設計接続規則の out-of-graph 著作資産への非伝播」＝#164（PR #246 merged）。既存 PROMPT ノード4件から backref 付与で在グラフ化。
> - **FND-79**「RULE-006/025/026 が複数 SPEC に分散し全体把握の負荷」＝#165。RULE 横断索引を `docs/doc-system/03-connection-matrix.md` §10 に整備、dashboard ✅ 矛盾は v2 で moot（v1 archive 化・PR8）を確認、`dsv2 reverse` で `必須上流辺の欠如`→FND-79 backref＋`fnd/resolved/` へ移動（孤立解消・618ノード green）。

> issue #94 のオーナー判断に基づき、v1→v2 移行 585 ノードの空 `scheduled` は backfill 済み。
> issue #152 で移行後追加ノードも含めて空 `scheduled` を禁止し、既存空欄は `sprint-1` に整理済み。

### open Q（1 件）

| タイトル（要約） | scheduled | 備考 |
|---|---|---|
| **SRC→[dm, port, orc] が MOD を対象外＝実装担体の自然な張り先が無い**（Phase A・#160 前提） | 🗓 sprint-1 | **🔴 オーナー判断待ち（新規・2026-07-21）**。Python モジュールの自然な対応先は MOD だが SRC は張れない。選択肢①`src→[mod,dm,port,orc]`拡張（推奨）②現状維持③MOD一本化。決定は #160 SRC 著作の前提 |

> Q-2 は #157 で DD-23 へ昇格し、傘 SPEC マップ維持・実害顕在時細分化方針として decided 化済み。

### deferred PEND（1 件）

| タイトル（要約） | 備考 |
|---|---|
| 分析層の図（コンテキスト図・DFD）の手動メンテをスクリプト自動生成へ置換 | 🗓 sprint-1（backfill）。本文方針は sprint-2 以降で検討（VAL-5/FR-15） |

---

## 🔥 推奨ネクストアクション

| # | アクション | 優先 | 根拠 / 状態 |
|---|---|---|---|
| N1 | 実装（FR-10：spec-inspector CLI） | 🔵 低 | Python 標準ライブラリのみ。凍結セット確定後 |
| N2 | テスト戦略④（凍結セット残項目） | 🟡 中 | 設計層著作済み。`/test-strategy` スキルで TD/TC 設計 |
| N3 | ダッシュボード（open Q/FND/DD 等）の自動集計サブコマンド | ✅ 完了 | [issue #108](https://github.com/hiratashinnya/review-system/issues/108) 対応として `python3 -m dsv2 dashboard --root doc-system-v2` を追加済み。stage/type/status 件数と `fnd/open`・`q/open`・`dd/decided`・`pend/open|deferred` の Markdown 集計を stdout に出し、本帳票の手書き要約を検算できる |
| N4 | #94 scheduled backfill | ✅ 完了 | v1→v2 移行 585 ノードの空 `scheduled` を `sprint-1` へ backfill 済み。既存値あり・移行後追加ノードは保持 |
| N5 | #142 docidx archive 判断 | ✅ 完了 | `docidx/` は v1 archive CLI と v2 共有 `docidx.nodeyaml` として残し、物理 archive へ移動しない。現行 v2 照会は `dsv2` へ寄せる |
| N6 | #140 → #141 config 操作エージェント | 🟡 中 | #140 doc_system 側は完了。次は #141 review_system 側へ横展開する。#4 は doc_system 側を #140 で吸収し、review_system 側は #141 の完了時に close 判断する |
| N7 | #158〜#165 stage completion 前処理 | 🔴 高 | #157 Q-2 DD 化、#158 lifecycle 整理、#159 SPEC 本文系 FND 解消は完了。次に Sprint 1 open FND 解消（#165/#164）、stage gate（#163）、SRC/TD/TC/TR materialization（#160/#161）、`current_stage` advancement（#162）の順で #127 完了判定へ進む |

---

## 今後（自動化の別 issue）

本ダッシュボードは**手で書いた最小版**（オーナー方針・2026-07-05）として継続する。open FND/Q/DD/PEND を
`doc-system-v2/nodes/04-verification/**` から検算する集計は
`python3 -m dsv2 dashboard --root doc-system-v2` で Markdown スナップショットとして標準出力へ生成する。
全面自動生成への置換はせず、当面は手書きの物語部分と機械集計の照合で運用する。

---

## 📌 運用メモ
- 本帳票は **out-of-graph**（ノードを持たない要約帳票。`docs/doc-system/config.yaml` の `trace_scope.exclude` 対象は v1 パスのみだが、本ファイルは `doc-system-v2/` 直下でノード対象ディレクトリ `nodes/**` の外にあるため元々対象外）。
- **状態と優先度の要約**に絞る。FND/Q/DD の明細は各ノードファイルを参照（全件列挙はしない）。
- 手書き要約の検算には `python3 -m dsv2 dashboard --root doc-system-v2` を使う。`meta.json` が古い場合は
  先に `python3 -m dsv2 index --root doc-system-v2` を再実行する。
- 判断待ちは確定したら「次アクション」を実行し本帳票から消す。**決定の経緯は DD/PEND ノードに残す**（消さない＝PR8）。

## 参考ドキュメント
- **新フォーマット定義**: [`doc-system-v2/FORMAT.md`](FORMAT.md) — 1ノード1YAML・型別 body policy・slug id・サイドカー schema
- **記法ガイド**: [`doc-system-v2/notation.md`](notation.md)
- **グローバル設定**: [`doc-system-v2/config.yml`](config.yml) — 必須接続ルール・ステージ・condition 語彙・カバレッジ要件
- **dsv2 CLI**: [`dsv2/README.md`](../dsv2/README.md) — `dashboard` 集計コマンドを含む v2 ツール説明
- **移行レポート**: [`doc-system-v2/MIGRATION_REPORT.md`](MIGRATION_REPORT.md) — v1→v2 一括移行（Sub-B）の全ノード対応表
- **v1 旧ダッシュボード（archive）**: [`doc-system-v1-archive/00-dashboard.md`](../doc-system-v1-archive/00-dashboard.md) — cutover 前の完了ログ・経緯（消さない＝PR8）
