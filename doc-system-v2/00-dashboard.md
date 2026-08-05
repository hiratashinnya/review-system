# doc-system-v2 ダッシュボード

> doc-system-v2（ドッグフーディング・ノードグラフ v2）の **進捗・判断待ち・ネクストアクション** の運用ハブ。
> **状態と優先度の要約**に絞る——明細（ノード属性・辺）は各ノード YAML（`nodes/**/{slug}.yaml`）、
> 本文は型別 body policy に従う Markdown、
> 本帳票は要約のみ。**全件列挙はしない**。
>
> **最終更新**: 2026-08-04 ｜ **current_stage**: `design`（`docs/doc-system/config.yaml`）
> 本帳票は **v1 の `doc-system/00-dashboard.md` の後継**（issue #76・v1→v2 cutover）。v1 は
> `doc-system-v1-archive/`（旧 `doc-system/`・`git mv` で履歴保持）へ retire 済み。**正本は本コーパス
> （`doc-system-v2/nodes/**`）**。旧ダッシュボードの経緯・完了ログは archive 側に保全されている
> （消さない＝PR8。参照する場合は `doc-system-v1-archive/00-dashboard.md`）。

---

## 🔄 直近の作業

| 作業 | 種別 | 状態 |
|---|---|---|
| 処置計画の永続化と Phase 0（2026-07-28） | 計画の Issue 階層化＋起票バッチの内部矛盾是正 | 🟡 Phase 0 実施中（2026-07-28）。#127 までの残作業を**3 層 Issue 階層へ永続化**（親 #261 ＝取りまとめ／子 #262-#265 ＝Phase 0-3／孫 ＝#266 と既存 #253-#256・#160-#162）。オーナー確定判断 J1〜J4 を #261 に記録。**Phase 0** では、未マージのまま陳腐化していた `claude/doc-system-dashboard-issue-check-8gq7ay` の起票コミット（`747aa07`）を取り込み、**同バッチが自ら生んだ内部矛盾 2 件を確定記録に入れる前に是正**——①Q ノードの母数が著作時点の値（128＝open 11+resolved 117）のままで、同バッチが FND を 3 件足した結果と不整合（正＝**131＝open 14+resolved 117**）②同 Q が「深刻度行を欠く resolved を特定できたのは 3 件」とする一方、同バッチの FND は edges で**4 件すべて特定済み**。あわせて同型の母数誤りが当該 FND 本文にも残存していることを実測で検出し是正。ダッシュボード側は訂正コメント/#163 close の「未実施」記述と N7 を実態へ更新し、N8 の PR7 様式違反（機構選択の競合を伏せた推奨）を明示、N9 に計画階層を追記。**推奨（Q の選択肢③）は母数訂正後も不変**。 |
| ダッシュボード・Issue 棚卸し（2026-07-27） | 検算→未起票論点の在グラフ化→処置計画 | 🟡 起票完了・オーナー判断待ち（2026-07-27）。ダッシュボード記載を機械実測で全件検算し**一致を確認**（632ノード／ERROR 53／drift 0／prompt-coverage 0／open FND 11・Q 1・PEND 2＋1）。その上で **①ダッシュボードに直書きされ在グラフ化されていなかった判断待ち（深刻度基準の遡及適用）を Q ノードへ起票**し、著作過程で判明した **FND 3 件**（深刻度の語彙不一致・深刻度行の欠落 4 件・`docs/doc-system/` 4文書の v2 未追随）を追加起票（計 4 ノード＝632→636・**ERROR 増ゼロ**）。あわせて **Issue 側の陳腐化 3 件**（#253〜#256 の「実施スプリント未設定」記述が CLAUDE.md 2026-07-26 改訂と矛盾／同 4 Issue の「FND 未起票」注記が起票済みと乖離／**#163 は受け入れ条件充足済みだが OPEN**）を検出。**3 件とも 2026-07-27 中に処置済み**（#253/#254/#255/#256 へ訂正コメント投稿・#163 は completed で close）。ただし **#160 は同じ「実施スプリント未設定」記述を持ちながら訂正バッチから漏れた**（Phase 1・#263 で処置）。 |
| issue #160/#253 — 必須辺検証ルールの見直し（全型監査） | 規則監査→Issue 分割→FND/Q 起票 | 🟡 起票完了・処置待ち（2026-07-26）。53 ERROR の内訳を全数照合したところ、**規則の分類粒度不足だけで解消する純粋な false positive は `p←mod` 3 件＋`scm←cfg`（傘）2 件＝計 5 件のみ**で、**残り 46 件（`p←mod` 39・`scm←cfg`（成果物）5・`d←p` 2）はオーナー確定方針の適用後もノード・辺の実著作を要する**（`p←mod` 39 は leaf P への MOD 割り当て＝既存 MOD からの張り替えが中心、`scm←cfg` 5 は O/I→SCM 辺の新規著作）。`ds←prs` 2 は規則不備か未著作かが未決（Q）。従来「全件 backlog・規則欠陥ではない」→ 中間時点で「`p←mod` 42・`scm←cfg` 7 は規則側の欠陥」としていた分類はいずれも訂正する（PR #257 の Codex レビュー指摘・2026-07-26 で判明）。implementation 段の `src` 系規則にも 3 欠陥（必須辺の非対称／非 Python 担体の非被覆／CFG 粒度ミスマッチ）を検出し、**#160 の前提ブロッカー**と判定。シリーズ Issue #253(①scm←cfg)/#254(②p←mod)/#255(③ds←prs＋d←p)/#256(④src 系) に分割し、在グラフへ FND 10 件＋Q 1 件を起票（632ノード・ERROR 53 件で baseline 維持）。`p←mod` はオーナー確定で **「全 leaf が MOD を要する（推移的被覆は不採用）」**方針（MOD:P は1:1でなくてよい・既存 MOD への割当で新設不要・DD-13 改訂＋leaf 限定規則の分離は視野）。#160 のスコープは**維持**（設計実装乖離を切り出さず、整合作業を #160 内で行う）。**関連 Issue #254/#160 本文は本確定方針に反する記述が残っていたため訂正コメントを追記済み**（#254＝推奨A「推移的被覆」を訂正、#160＝ORC `著作・反映パイプライン実行` の材化可否を訂正）。 |
| issue #159 — SPEC 本文系 open FND 解消 | SPEC-3-1/13/9-1+10/31 の文言・親辺・resolved 化 | ✅ 完了（2026-07-11）。対象4件を `fnd/resolved/` へ移動し、処置先 SPEC から backref を付与。 |
| issue #158 — 本文 resolved 済み open FND 整理 | lifecycle 配置整理 | ✅ 完了（2026-07-11）。`_drift` z バンプ誤検出と `backref check` open-but-backref 判定トートロジーの 2 件を、既存 backref と out-of-graph 対象の扱いを確認した上で `fnd/resolved/` へ整理。 |
| issue #152 — scheduled 空欄対策 | 流入防止＋流出検出＋既存空欄整理 | ✅ 完了（2026-07-10）。`scheduled` を非空必須にし、`validate.py` / `schema/sidecar.schema.json` / `dsv2 index` で空欄・欠落を fail-close。移行後追加の空欄 12 件は完了済み/解決済みノードとして `sprint-1` に整理。 |
| issue #161/#163 — 接続規則の価値経路充足性 見直し（Phase A） | ルール監査→DD-9→config反映→in-graphミラー | 🟡 反映済み・施行待ち（2026-07-21）。オーナー確定で **DD-9** を起票し、価値経路の下流連続性規則（p←mod / scm←cfg / ds←prs〔design〕・mod・dm・port・orc・prs・prompt・cfg←src〔impl・シンボル適格性条件付き〕）＋ nfr←spec・spec←td(leaf限定) の error 昇格を `doc-system-v2/config.yml` へ**一括反映**（分割せず）。in-graph は dedicated rule SPEC 10・severity 是正 2・傘改訂・CFG `must_be_linked_from` 同期で追随（618ノード・validate/drift/coverage 全green）。**規則は宣言のみで inert＝施行は #163 Phase B（must_be_linked_from reader 実装）で発火**。Phase A FND は施行完了まで open 維持。SRC シンボル適格性はオーナー再確認待ち（下記 N8）。 |
| issue #157〜#165 — stage completion issue expansion | 進捗管理ファイル更新 | 🟡 一部完了（2026-07-11〜2026-07-27）。#157 Q-2→DD-23、#158/#159 で FND 6 件 resolved、#164（FND-99）／#165（FND-79）resolved、#163 gate 施行 merge 済み。**残りは必須辺規則の是正（#253/#254/#255/#256）→ SRC materialization（#160）→ TD/TC/TR materialization（#161）→ `current_stage` advancement（#162）**（順序と根拠は N8）。 |
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
| 02-what | `nodes/02-what/` | 263 | FR / NFR / SPEC |
| 03-analysis | `nodes/03-analysis/` | 98 | ACTOR / I / O / D / P / E / TERM |
| 04-verification | `nodes/04-verification/` | 190 | TD / TC / TR / VERIFY / FND / DD / Q / PEND |
| 05-design | `nodes/05-design/` | 78 | ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT |
| **計** | `nodes/**` | **643** | v1 移行後の増分著作を含む現行実測 |

> ノード数は `python3 -m dsv2 index --root doc-system-v2` の 2026-08-05 実測（640→643。PR #326——
> PR #326 自身のレビュー指摘（R-06/R-07）を在グラフ化：FND「検証結果が主文脈経由で writer へ渡り
> 2段分離の fail-close を迂回できる」（ERROR）・DD「FND 起票単位は機序で分け対象集合が同型の指摘は
> 既存 FND のスコープ拡張とする」（decided・R-07 の起票単位決定）・Q「オーナー決定の出所表記を
> in-repo でどこまで検証可能にするか」（open）を新規 3 件起票。既存 open FND 4 件（段落分割
> 0.1.0→0.1.1／段落選定条件 0.1.0→0.1.1／検査対象探索 0.1.0→0.1.1／dsv2 実装 6 モジュール
> 0.2.1→0.2.2）はすべて **z バンプ**（本文修正・上記 DD への backref 辺追加のみ・x.y 不変のため
> 依存元への ref_version 伝播なし・新規ノードではない）。直前の 636→640 は PR #319（Issue #315）起点
> の tmp 掃除ガード追従テスト指摘 FND 4 件。さらに直前の 632→636 は深刻度の判定基準・語彙・本文項目に
> 関する FND 3 件＋Q 1 件（2026-07-27）。さらに直前の 621→632 は必須辺規則の欠陥・設計実装乖離の
> FND 10 件＋Q 1 件（2026-07-26・#253/#254/#255/#256/#160）。`doc-system-v2/meta.json`
> が古い場合、照会系コマンドは古い集計を読むため、最新値確認前に `index` を再生成する。
> **2026-08-05 時点**: `python3 doc-system-v2/validate.py` は **643ノード / validate ERROR 53 件**
> （p←mod 42/scm←cfg 7/ds←prs 2/d←p 2）。**本バッチ起票・更新による ERROR 増はゼロ**（baseline 維持）。
> drift 0 件・PROMPT coverage 欠落 0 件。
> `python3 -m dsv2 drift` は drift 0 件、`python3 -m dsv2 prompt-coverage` は PROMPT coverage 欠落 0 件。
>
> **⚠️ 53 ERROR の分類を再訂正（2026-07-26・オーナー確定方針の反映後。PR #257 の Codex レビュー指摘で判明）**:
> 当初「全件が #160/#161 の backlog＝規則欠陥ではない」としていたのを、全数照合で「`p←mod` 42 件と
> `scm←cfg` 7 件は規則側の欠陥、純粋な未著作は `d←p` の 2 件のみ」と訂正したが、**この中間分類も不正確
> だった**。オーナー確定方針（`p←mod`＝全 leaf が MOD を要する／`scm←cfg`＝3部分集団に分割）を適用すると、
> 規則の分類粒度不足だけで解消する**純粋な false positive は `p←mod` 3 件＋`scm←cfg`（傘）2 件＝計 5 件**
> にとどまり、**残り `p←mod` 39 件（leaf への MOD 割り当て）＋`scm←cfg`（成果物）5 件（O/I→SCM 辺の新規
> 著作）＋`d←p` 2 件＝計 46 件は規則を直しても別途ノード・辺の実著作を要する**。`ds←prs` 2 件は規則不備か
> 未著作か未決のまま。それぞれ #254 / #253 / #255 で扱う。

---

## ⏳ オーナー判断待ち（open FND / Q / PEND 要約）

**計 25 件**（open FND 19・open Q 3・open PEND 2・deferred PEND 1）。明細は各ノードファイル（`nodes/04-verification/{fnd,q,pend}/**`）を参照。

> **⚠️ 深刻度判定の基準を是正（2026-07-26・オーナー指示）**: 従来は「`validate.py` が現に落ちるか」
> 「検査する規則があるか」＝**機械検出可能性**を深刻度の根拠にしていた（先例＝FND-96「live RULE 失敗を
> 伴わない原則違反は WARNING」）。この基準は「**機械が見られない欠陥ほど軽く扱われる**」逆転を生み、
> PR2「機械判定と運用ルールを混ぜない」に反する。以後 **深刻度は実害で判定する**。
> 本方針により既存 FND 1 件（`dsv2-実装-6-モジュールに対応する設計ノード-mod-p-が存在しない`）を
> WARNING → ERROR へ是正した（v0.2.0）。**既存 FND への遡及適用の要否は Q ノード「深刻度の判定基準是正を
> 既存 FND 全件へ遡及適用するか」へ起票済み**（2026-07-27）。従来この判断待ちは本帳票に直書きされたまま
> 在グラフ化されておらず、CLAUDE.md「質問はダッシュボードに直接書くのではなく Q ノードを起票し、
> ダッシュボードはその要約を更新する」に反していたため是正した。**深刻度はサイドカーのキーではなく本文の
> 散文であり機械消費されない**（`sidecar.schema.json` に severity 系キーなし）ため、再判定しても
> validate/drift/CI の結果は変わらない＝効果はトリアージ入力の質に限られる。あわせて深刻度の**語彙**と
> **本文必須項目**にも不整合が見つかり FND 3 件を起票した（下表）。

> **⚙️ 施行状態（2026-07-26 更新）**: `must_link_to`/`must_be_linked_from` が施行器（#163）で稼働。
> `validate.py doc-system-v2` は **632ノード / 53 ERROR** が baseline（p←mod 42/scm←cfg 7/ds←prs 2/d←p 2）。
> **内訳の分類は 2026-07-26 に再訂正済み**（純粋な規則欠陥＝false positive 5／規則直し後も実著作を要する
> 46〔`p←mod` 39・`scm←cfg` 5・`d←p` 2〕／未決 2＝`ds←prs`。上表の注記を参照）。
> drift 0・prompt-coverage 0。既存テスト/CI は不変（合成 fixture・pages.yml 非 validate）。

### open FND（19 件）

| タイトル（要約） | scheduled | 対応 Issue | 備考 |
|---|---|---|---|
| config の `SPEC→[FR, NFR, SPEC]` OR 規則のループホール | 🗓 sprint-2（承認済） | — | v1 時代の FND-35 相当。オーナー承認済み |
| `scm←cfg` 規則が SCM 型内の3部分集団を区別せず一律に CFG 入辺を要求する | 🗓 sprint-1 | #253 | 規則不備。config 4(PASS)/成果物 5/傘 2 に分かれる。live ERROR 7 件のうち**規則直しのみで消える false positive は傘 2 件**、**残り成果物 5 件は O/I→SCM 辺の新規著作を要する** |
| `p←mod` が全プロセスに MOD を要求し DD-13 の混合粒度と矛盾する | 🗓 sprint-1 | #254 | 規則不備。live ERROR 42 件のうち**規則直しのみで消える false positive は non-leaf 3 件のみ**、**残り 39 件は leaf P への MOD 割り当て（既存 MOD からの張り替え中心）という実著作を要する**。オーナー確定方針＝**全 leaf が MOD を要する（推移的被覆は不採用）**・MOD:P は1:1でなくてよい・既存 MOD 12 件（non-leaf 指し先）は規則の要求対象から外れ張り替えが必要 |
| 消費プロセスが特定済みの D 2 件に `P→D` 消費辺が未著作 | 🗓 sprint-1 | #255 | **規則側に欠陥なし**（D 21 件中 19 件充足）。消費関係は両 D の本文に散文で存在するが辺として存在しない。live ERROR 2 件 |
| `src` の必須出辺の許容先4型と `src` を要求する入辺規則7型が非対称 | 🗓 sprint-1 | #256 | 規則不備。prs/prompt/cfg 専用 SRC が詰む。**#160 の前提ブロッカー**。implementation 段で発火（現在 latent） |
| `src_symbol_eligibility` が担体軸を持たず非 Python 担体の MOD/PRS/ORC を被覆しない | 🗓 sprint-1 | #256 | 規則不備。`author`/`reconciler`/ORC `著作・反映パイプライン実行` の実体は `.claude/agents/*.md`。既存 `carrier` enum で判別可能。**v0.2.0 で ORC を追加（初版は網羅漏れ）・v0.2.1 で改名** |
| `cfg←src` がキー単位の CFG にファイル単位の SRC を要求し粒度が一致しない | 🗓 sprint-1 | #256 | 規則不備。CFG 14 件が同一 `config.yml` を指すことになる |
| 設計層 MOD/DM/TERM/PORT/PRS が宣言する実装担体 `spec_inspector/*` が実在しない | 🗓 sprint-1 | #160 | 設計実装乖離。**v0.2.0 で TERM 6 件を追加し 26→32 件全数に forward 辺（初版は網羅漏れ）・v0.2.1 で改名**。実装は `dsv2/` + `validate.py` に別分割で存在 |
| dsv2 実装 6 モジュールに対応する設計ノード（MOD/P）が存在しない | 🗓 sprint-1 | #160 | 設計外実装（上記の逆方向）。`viewer`/`rename`/`reverse`/`gitutil`/`yamledit`/`dashboard`/`cleantmp`。**v0.2.0 で深刻度 WARNING→ERROR へ是正・v0.2.1 で対象を 7 本へ拡張（オーナー判断 2026-08-04）・v0.2.2（z バンプ）で v0.2.1 のスコープ拡張の決定根拠を DD「FND 起票単位は機序で分け対象集合が同型の指摘は既存 FND のスコープ拡張とする」への backref 辺で在グラフ化**。タイトルの数詞「6」は起票時点の列挙数（改題せず本文に明記） |
| ORC `検査パイプライン実行` が実在しない CLI `python -m spec_inspector` を本文で参照している | 🗓 sprint-1 | #160 | 担体宣言行を持たないため上記 C1 とは別命題。実体は `doc-system-v2/validate.py:main`。SRC 著作時に `source.file` と本文が矛盾する |
| tmp 草案の出力先記述が v1 の1親1ファイル形式のまま1ノード2ファイル化に未追随 | 🗓 sprint-1 | #160 | agent 定義 8 ファイルは v2 ミラーレイアウトに追随済みだが、PRS/DS/ORC の設計層3件と `CLAUDE.md` L86 が v1 形式のまま。PRS 本文には廃止済み「YAML フロントマター」記述も同居 |
| FND の深刻度**語彙**が `05-verification.md`・v2 テンプレート・実コーパスで三者不一致 | 🗓 sprint-1 | #283 | **WARNING**。`critical/major/minor/info`（`docs/doc-system/05-verification.md` L212）／`low/medium/high（または ERROR/WARNING/INFO）`（`templates/verification/fnd.body.md`）／`ERROR/WARNING/INFO`（実コーパス 124/124 件）。推奨＝`ERROR/WARNING/INFO` へ一本化し非適合資産を同期 |
| resolved FND 4 件の本文に**深刻度行**がなくテンプレ必須項目を欠く | 🗓 sprint-1 | #283 | **INFO**。resolved 117 件中 113 件は保持（WARNING 80/INFO 20/ERROR 13）。4 件は同一 DD 起点のバッチで別骨格。推奨＝本文必須項目を検査する RULE 新設で再発を止める |
| `docs/doc-system/` の4文書が FND の**状態表現と本文項目**で v2 に未追随 | 🗓 sprint-1 | #283 | **WARNING**。①`01-document-items.md` L106 の「`resolved: true/false` で機械判定」は現に誤答（128 件中 117 件を取り違える）②`dsv2 reverse --apply` が本文/path 矛盾を確定的に生成（同型ドリフト 19 件が実発生済み）③`wontfix` の受け皿が存在しない。推奨＝文書同期を先行し `wontfix` の可否は切り出してオーナー決定 |
| tmp 掃除ガード追従テストの段落分割が空行基準で箇条書き・表内の保護名借用を見逃す | 🗓 sprint-1 | PR #319（Issue #315） | WARNING。N-02 是正が効いたのは dsv2/*.py のみ。Markdown 3 文書ではブロック全体が 1 段落＝借用の余地が残る。推奨=段落分割の Markdown 対応＋表は書式規約。**v0.1.1（z バンプ）で実測表の `dsv2/*.py` 行を借用の実例へ訂正**（初版の「.py には借用の余地なし」は事実誤り）。要点・選択肢1・選択肢3・推奨(a)の適用範囲を Markdown＋`.py` docstring へ是正、決着済み留保 2 件を決着記述へ更新 |
| 保護名追従テストの段落選定条件が実装 docstring の単一保護名記述を取りこぼす | 🗓 sprint-1 | PR #319（Issue #315） | WARNING。dsv2/cleantmp.py L3–7 が `_handoff` のみのまま検査対象外＝**現に見逃し 1 件**。推奨=記述の即時是正＋選定条件の見直し。**v0.1.1（z バンプ）で決着済みの留保を決着記述へ更新** |
| tmp 掃除ガード追従テストの検査対象探索がガード記述の消滅とミラー文書を見落とす | 🗓 sprint-1 | PR #319（Issue #315） | **ERROR**。①語依存の絞り込みでガード記述が消えた文書は黙って対象外になる ②候補リストが固定で 4 ツリーのミラー・in-graph PROMPT を初めから含まず**現に 3 件を取りこぼし**。推奨＝必須リスト(MUST)＋動的候補(MAY)の 2 層化、4 ツリー分は asset_parity と分担。**v0.1.1（z バンプ）で自己参照的な数値（リポジトリ全体で 7 件）を候補集合基準の表現へ言い換え＋DD backref 付与** |
| reconciliation の tmp 掃除ガードが in-graph PROMPT と Copilot・Codex ミラーに未同期 | 🗓 sprint-1 | PR #319（Issue #315） | **ERROR**。掃除ガードが `.claude/agents/reconciliation.md` にのみ反映され、PROMPT ノード／`.github` ミラー／`.codex` ミラーは「tmp/<sprint>/<parent-id>/ を削除する」のみで clean-tmp・保護名・rm 禁止をすべて欠く。PROMPT は Bash 許可用途に clean-tmp が無く掃除対象粒度も実体と不一致。推奨＝即時同期＋必須検査対象化 |
| 検証結果が主文脈経由で writer へ渡り2段分離の fail-close を迂回できる | 🗓 sprint-1 | PR #326 | **ERROR**。validator の判定がチャット文字列として主文脈経由で writer へ渡るため、writer 側に真正性の検証手段が無く DD-22 の 2 段分離を迂回できる。本 PR の書込時に**現に逸脱が発生**（writer がハンドオフで自己申告）。分析層 P「草案スキーマ検証」/P「本ファイル転記」が述べる「検証済み草案」の担体（D ノード）も存在しない（PR4/PR6）。推奨＝writer 側の決定論ツール（validate.py/check-slug/drift）再実行によるゲート化＋受領ブロックの形式検査 |

> **起票 10 件の追加（2026-07-26・オーナー承認済み）**: 必須辺検証ルールの見直しに伴い、`config.yml` の
> 必須辺規則が型内の部分集団を見落としている欠陥、および設計層と実装の双方向の乖離を在グラフ化した。
> いずれも処置方針の決定はオーナーに委ねており、**AI による「対応不要」の結論は含めない**。
> 起票による ERROR 増はゼロ（632ノード / 53 ERROR ＝ baseline 維持・drift 0・prompt-coverage 0）。
>
> **⚠️ 初版の網羅漏れ 2 件を是正（2026-07-26）**: 起票時に対象集合を**代理基準**（`config.yml` の
> `must_be_linked_from` 型リスト／既知の事例）から導出し、**FND 自身の判定述語で型横断の網羅確認を
> していなかった**ため、2 件でスコープが不足していた。①`spec_inspector` 担体 FND＝TERM 6 件漏れ
> （26→32）、②`src_symbol_eligibility` FND＝ORC 漏れ（MOD/PRS→MOD/PRS/ORC）。いずれも v0.2.0 で
> 是正し、原因を各 FND 本文に記録。あわせて `dsv2 rename` でタイトルを現行スコープへ同期（v0.2.1）。

> **resolved 済み（2026-07-21・本セッション）**:
> - **Phase A FND**「接続規則が価値経路連続性を error で機械保証していない」（#161 本体）。DD-9/DD-10 で規則を config 反映＋**#163 施行器 merge** で機械保証が成立→ finding 解消。`価値経路到達の充足判定`→FND backref＋`fnd/resolved/` へ移動。53 error 顕在化は #160/#161 backlog（別事象）・p←mod 過剰発火精査は #160/#161 follow-on として本文に保持。
> - **FND-99**「設計接続規則の out-of-graph 著作資産への非伝播」＝#164（PR #246 merged）。既存 PROMPT ノード4件から backref 付与で在グラフ化。
> - **FND-79**「RULE-006/025/026 が複数 SPEC に分散し全体把握の負荷」＝#165（PR #247 merged）。RULE 横断索引を connection-matrix §10 に整備、`dsv2 reverse` で resolved 化。

> issue #94 のオーナー判断に基づき、v1→v2 移行 585 ノードの空 `scheduled` は backfill 済み。
> issue #152 で移行後追加ノードも含めて空 `scheduled` を禁止し、既存空欄は `sprint-1` に整理済み。

### open Q（3 件）

| タイトル（要約） | scheduled | 対応 Issue | 備考 |
|---|---|---|---|
| `ds←prs` 規則を書き込み実装に限るか永続層アクセス実装へ読み替えるか | 🗓 sprint-1 | #255 | read-only DS 2 件（`config.yaml-ds`/`in-graph-ノードファイル群`）に PRS 入辺なし。規則不備か未著作かが未決のため FND ではなく Q。live ERROR 2 件 |
| 深刻度の判定基準是正を既存 FND 全件へ遡及適用するか | 🗓 sprint-1 | #283 | 母数＝**FND 131 件（open 14・resolved 117）**。判定根拠がほぼ未記録のため grep で切り分け不能＝全件遡及は約 100 件の人手読み直し。**深刻度は機械消費されず validate 結果は不変**。選択肢＝①全件遡及／②遡及せず以後のみ／③限定遡及。推奨＝③＋基準の in-graph 明文化（母数訂正後も**不変**）。**本バッチ（PR #326）では変更なし**（草案なし・依存元 FND「dsv2 実装 6 モジュール…」の z バンプで x.y=0.2 不変のため `ref_version "0.2"` の伝播も不要） |
| オーナー決定の出所表記を in-repo でどこまで検証可能にするか | 🗓 sprint-1 | PR #326 | 「オーナー判断（日付）」の実在をリポジトリ内から検証できない（根拠はチャットと gitignore 済みハンドオフのみ）。チャット指示は系外事象で観測不能（PR3/PR4）ゆえ証明は原理的に不可、可能なのは区別。選択肢＝①現状維持／②外部参照併記の必須化／③記録形式の規定／④出所表記を弱める。推奨＝③基軸＋重要決定のみ②併用・遡及は以後のみ |

> `q/open/` ディレクトリは本起票（2026-07-26）が初出のため新規作成した（`decided`/`closed` は既存）。
> Q「SRC→[dm,port,orc] が MOD を対象外」は **DD-10 へ昇格し decided 化**（2026-07-21）。オーナー確定＝`src→[mod,dm,port,orc]` 拡張①。`q/decided/` へ移動。
> Q-2 は #157 で DD-23 へ昇格し、傘 SPEC マップ維持・実害顕在時細分化方針として decided 化済み。
>
> **DD 新規追加（2026-08-05・PR #326）**: `dd/decided/` に「FND 起票単位は機序で分け対象集合が同型の
> 指摘は既存 FND のスコープ拡張とする」を追加（2026-08-04 オーナー決定 2 件——起票単位の決定・FND #160
> のスコープ拡張——の in-repo 記録・R-07 是正）。`edges: []`（RULE-001）で被参照は上表 FND 2 件からの
> backref＋Q「オーナー決定の出所表記を…」からの参照辺 1 本により確保（本帳票に DD 一覧の節は無いため
> 注記のみ・明細は `nodes/04-verification/dd/decided/` を参照）。

### open PEND（2 件・DD-10 起票・2026-07-21）

| タイトル（要約） | scheduled | 備考 |
|---|---|---|
| **SRC シンボル適格性の多言語拡張と class 適格性厳密化**（PEND-a） | 🗓 sprint-1 起票 | 適格性規則は Python 前提（source.kind 語彙・AST 解析）。言語別切替/言語非依存化での多言語対応＋DM/PORT の class 厳密化（Protocol/dataclass 判定）。**実施時期はオーナー判断**（独断 defer せず） |
| **非 Python 担体（prompt/cfg）の内容が当該資産である意味判定の完全機械化**（PEND-b） | 🗓 sprint-1 起票 | `.md/.yml` の中身の意味判定は現状不可。sprint-1 は存在＋正規パス規約一致まで機械判定。完全機械化は将来課題。**実施時期はオーナー判断** |

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
| N7 | #158〜#165 stage completion 前処理 | 🔴 高 | #157 Q-2 DD 化、#158 lifecycle 整理、#159 SPEC 本文系 FND 解消、#164（FND-99）／#165（FND-79）解消、#163 gate 施行はいずれも**完了**（#163 は 2026-07-27 に completed で close 済み）。次は下記 N8 の順序で #127 完了判定へ進む |
| N8 | design 段 53 ERROR の解消 → stage 前進 | 🔴 高 | **処置計画を Issue 階層へ永続化済み（2026-07-28・親 #261）**。順序＝**#266（機構選択の実測・#253 のブロッカー）／#255（ds←prs 2＋d←p 2・機構非依存で並行可）→ #253（scm←cfg 7）→ #254（p←mod 42）→ #256（src 系規則）→ #160（SRC materialize）→ #161（TD/TC/TR materialize）→ #162（stage 前進）**。#253/#254/#256 は**同一機構の欠落**（`dsv2/query.py` の `applies_when` が `condition_present` にハードコードされ部分集団を表現できない）に帰着するため #253 で機構を確立してから #254/#256 が再利用する。⚠️ **本欄は当初「#253 で汎用述語機構を確立」を前提に順序を推奨していたが、#254 に記録済みのオーナー方針（leaf 限定規則を専用ブロックへ分離する案）と競合しており、片方だけを提示していた（PR7 の様式違反）。機構選択は #266 で実測・比較してからオーナーが決定する**。#256 は #160 の前提ブロッカー。TD/TC/TR は現在 **0 件**（ディレクトリ自体が不在）で #161 は完全未着手 |
| N9 | 処置計画（#261）の進行 | 🔴 高 | 3 層 Issue 階層。**#262 Phase 0**（本ブランチの是正・取り込み）→ **#263 Phase 1**（#160 訂正コメント漏れ・新規 FND/Q の Issue 化・#253 本文の陳腐化）→ **#264 Phase 2**（= N8 の規則是正群）→ **#265 Phase 3**（materialize→stage 前進）。オーナー確定判断 J1〜J4 は #261 本文に記録 |

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
