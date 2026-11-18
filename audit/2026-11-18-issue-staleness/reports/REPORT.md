# 全Issue 陳腐化・進捗前提の棚卸し（2026-11-18）

## 結論

**444 Issue（Open 139、Closed 305）の全本文を取得・逐件メモ化し、PR 406件（merged 370、closed unmerged 31、open 5）の現在状態と横断照合した。** 444個のメモファイル、全本文のスナップショット8本、全件INDEX、重要候補の個別実査メモを監査専用ブランチに保存。main、既存 Issue/PR、ACは一切変更していない。

- 初期基準 main: f2b61188a1600d0e1048dd38db2c2379809e68aa。現行mainのbaseline.jsonは **27 module_lines + 17 comment_blocks + 0 mixed_class_files = 44件**。
- 2026-06〜11（6月・9月・10月・11月は全月、7月・8月は前半/後半）× open/closed で検索上限100件未満に分割。2026-05以前は検索0件。取得結果を issue number で重複検査し444件。
- 一次の参照先・語彙抽出はPRの昔の状態を現在の誤りと取り違える**偽陽性**を含む。以下は本文の実査とmainの一部ファイル確認・主要PRの状態確認により分類を補正したもの。

## P1：まず整合させたい（旧完了ゲート・現行方針・契約）

| Issue | 確度 | 調査結果 | 推奨 |
|---|---|---|---|
| [Issue #273「PR #259/#260/#268 レビュー指摘・残課題の処置トラッキング」](https://github.com/hiratashinnya/review-system/issues/273) | 確認済 | 元の完了ゲートが PR #259/#260 の main 統合を要求するが、両PRは closed / unmerged。PR #268 は merged。#575 で別設計へ置換された。現行ゲートのままでは完了不能。 | #575および子#605/#606/#607を正規の承継先にし、元PRの統合を要求するACと旧ブロッカーをオーナー判断で廃止・移管する。旧レビュー証拠は残す。 |
| [Issue #290「PR #259: agy-delegate の workspace / fail-close gate を安全に成立させる」](https://github.com/hiratashinnya/review-system/issues/290) | 確認済 | 対象 PR #259 は closed / unmerged。main 取り込みを条件とするACは達成し得ない。#575は新しい直接実行へ移行し、#607は撤去未完了。 | 本Issueを旧版履歴に整理し、残っているfail-close・workspace要件を#606/#607または別Issueで充足するか検証。#607の実行前に#284等を無条件クローズしない。 |
| [Issue #291「PR #260: silent-failure 診断資産と codex-review の安全な実行契約を確立する」](https://github.com/hiratashinnya/review-system/issues/291) | 確認済 | 対象 PR #260 は closed / unmerged。#605がsilent-failure共通スキルを再実装済み。ただし#575はcodex-review固有の安全契約を再実装対象外としている。 | PR #260 のマージ・retarget・closingIssuesReferences確認ACは現行方針と整合せず再設計。残存codex-review契約を#285または新Issueへ紐付ける。 |
| [Issue #284「agy-mcp-bridge のローカルパッチを更新・再 clone 後も安全に維持する」](https://github.com/hiratashinnya/review-system/issues/284) | 条件付き陳腐化 | Issue目的は外部 agy-mcp-bridge のpatchを維持すること。#575でbridge撤去へ方針転換したが、#607のユーザー環境での撤去は未実施。 | #607の撤去を正規に実測するまで安全対策を勝手に解除しない。撤去後にパッチ維持要件の不要化を根拠付きで決定する。 |
| [Issue #745「[Tracking / Refactor] maintainability_lint 既存負債75件を全解消する（33ファイル・領域別stack）」](https://github.com/hiratashinnya/review-system/issues/745) | 確認済 | 本文冒頭の初期負債75件・33ファイルは2026-11-06時点。現行mainのmaintainability_lint/baseline.jsonはmodule_lines 27、comment_blocks 17、mixed_class_files 0、計44件。PR #696/#697/#740/#741もすべてmergedで、本文はopenとする。 | 初期75件を履歴値として残し、現状44件を別節へ明記。26子Issueの完了状況・変更ファイル・今後のstack基準を更新。#858/#859とのI系重複を整理。 |
| [Issue #858「[Tracking / Simplification] Claude Code標準worktreeを活用し、worktree所有台帳とgitgateの重複制御を縮小・撤去する」](https://github.com/hiratashinnya/review-system/issues/858) | 新設・整合調整 | 既存のworktree所有台帳/独自gitgateを標準worktreeへ置換する新方針。#745のI-01〜I-05（#752〜#756）が同じモジュールを責務分割する計画と重なる。 | #859の実測・オーナー方針確定まではI系の独立リファクタを無調整で進めない。#559/#662/#855との役割分担を確定する。 |
| [Issue #859「[Spike / Architecture] Claude Code worktree標準機能の実測・既存安全契約との照合・関連Issue再編を確定する」](https://github.com/hiratashinnya/review-system/issues/859) | 新設・有効 | #858のSpikeとして削減/保留すべき台帳機能、handoff/継承/再開の安全不変条件、既存Issueの再編を判断する。2026-11-18に更新された現行Issue。 | 当該Issueの採否判断を#745 I系子Issueのスコープ・AC・blocked-by整理の入力とする。Spike自体は陳腐化していない。 |
| [Issue #805「docs(karte): model.py 入口の docstring 要約化後、同「改ざん防止の機械的裏付けと既知の限界」節を名指す4文書の参照先を rationale へ更新する（F-799-07）」](https://github.com/hiratashinnya/review-system/issues/805) | 確認済 | PR #799 は2026-11-11にmerged。mainのkarte/model.pyは79行で詳細の所在を.ai/rationale/karte-module-split.mdに移設済み。現行文書の一部は旧docstringの詳細を探す。 | 現行説明の参照先を入口＋rationaleに更新。governance-directivesの過去の編集履歴コメントは歴史的証拠として保持し、機械的に一律書換しない。 |

## P2：依存解消・着手前提の更新・再実測

| Issue | 確度 | 調査結果 | 推奨 |
|---|---|---|---|
| [Issue #285「CLAUDE.md の codex-review 要約を正本の安全な実行契約へ同期する」](https://github.com/hiratashinnya/review-system/issues/285) | 再評価要 | 旧 PR #260 のcodex-review安全要約同期が対象だが PR #260 はclosed / unmerged。#605/#575の再実装範囲からcodex-review固有契約は明示的に外されている。 | 現行のcodex-review実行入口と正本を再読し、未移管の防御規定だけを移管。無条件クローズはしない。 |
| [Issue #752「[Maintainability I-01] SubagentStop判定・進行ポインタを分離」](https://github.com/hiratashinnya/review-system/issues/752) | スコープ競合可能性 | SubagentStop判定・進行ポインタを分離する計画が#858の台帳・後処理の縮退方針と交差。#722の安全修正は完了。 | #859で残す判定と撤去する状態を確定し、無駄な分割を避ける。 |
| [Issue #753「[Maintainability I-02] subagent bind・成果物回収・解放を分離」](https://github.com/hiratashinnya/review-system/issues/753) | スコープ競合可能性 | subagent bind・回収・解放の責務分割が#858の標準worktree活用・bind縮小に関係。 | #859で存続契約と改修順を再決定する。 |
| [Issue #754「[Maintainability I-03] worktree ledgerの保存・排他制御を分離」](https://github.com/hiratashinnya/review-system/issues/754) | スコープ競合可能性 | worktree ledger保存と排他の分割計画。#858では台帳自体の縮小・撤去を検討。 | 保存系分割の着手前に#859の方針を参照する。 |
| [Issue #755「[Maintainability I-04] worktree ledger状態遷移・残留検出を分離」](https://github.com/hiratashinnya/review-system/issues/755) | スコープ競合可能性 | worktree ledger状態遷移/残留判定の分割計画。#858では状態機械と残留ゲートを縮小対象とする。 | #859の状態・実体対応を反映してACを見直す。 |
| [Issue #756「[Maintainability I-05] durable_lockとSessionStartの小規模負債を解消」](https://github.com/hiratashinnya/review-system/issues/756) | スコープ競合可能性 | durable_lock/SessionStart等を分割する計画は、#858での台帳・lockの存続判断と重なる可能性。 | 存続するlock責務と単独残す機能を特定してから着手。 |
| [Issue #714「issue_start／karte 周りの記述がコードと食い違っている箇所を是正する（入れ子委譲・bind・GATED_ROLES・karte check）」](https://github.com/hiratashinnya/review-system/issues/714) | 一部確認済 | 現在の.ai/Individually-managed-lists.mdはSubagentStartがlinked worktreeを『割り当てる』と説明するが、issue_start/subagent_hooks.pyのrun_bindは既存dispatchのworktreeを束縛する。#614はPR #850で修正済み。 | (2)の文書を実装に同期。(4)のkarte check説明は#614後のmain実装で別に再現して残否を判断。旧PR #712の未統合記述も更新。 |
| [Issue #802「[#375 子3] Claude pr-reviewer 実機で finding が欠落なく karte へ取り込まれることを実測する」](https://github.com/hiratashinnya/review-system/issues/802) | 確認済 | 前提 PR #697 は2026-11-11にmerged、子 #800 はclosed。Issue本文はPR #697をdraftとして説明する。Claude実機のfinding欠落無しを実測するACはなお未完。 | 着手待ちを解除し、正規実機・証拠・環境/OIDに基づいて検証。単体試験だけでpassにしない。 |
| [Issue #803「[#375 子4] pr-reviewer の権限分離を機械で強制する（PR コメント投稿経路・worktree 隔離・Write パス制限の hook 依存）」](https://github.com/hiratashinnya/review-system/issues/803) | 確認済 | 前提 PR #697・子 #800 は統合済み/closed。本文に未マージstackを前提とする表現が残る。権限分離の強制自体は別課題として有効。 | 現行main基準でWrite制限・PR投稿・hook停止時の境界を検証。実装前提のみ更新。 |
| [Issue #810「[reviewer 取り込み経路の実害指摘3件] Write 検査の相対パス解決・karte 拒否文の誤誘導・申告原本の再試行時の食い違い（#375 / PR #697 再レビュー由来）」](https://github.com/hiratashinnya/review-system/issues/810) | 確認済 | PR #697と下段#696はmerged。本文はそのstackがmainに入るまで着手不能としている。指摘3件の実行再現は起票時点で未実施。 | 着手条件更新のうえ、3事象を現行mainで個別再現し、実害を区別して処置判断。 |
| [Issue #792「[重複実装の統合] karte ingest の owner scope 適用・karte_notify の shell 解析・review envelope 語彙を1箇所へ（#375 / PR #697 レビュー由来）」](https://github.com/hiratashinnya/review-system/issues/792) | 確認済 | 対象コードはPR #697/#696のmain統合待ちと記すが両PRはmerged。実装の重複3件が現存するかは別確認が必要。 | 最新mainで重複箇所と#751、#785の実装範囲を再点検して小さな独立修正へ。 |
| [Issue #793「[書式の食い違い] binding の run_id / target_key は任意の1行を許す一方 karte review envelope は header-safe のみ受理し、該当 binding で Codex pr-reviewer が必ず失敗する（#375 / PR #697 レビュー由来）」](https://github.com/hiratashinnya/review-system/issues/793) | 確認済 | 旧PR #697/#696統合待ち記述は古い。bindingの受理集合とreview envelope header-safeの食い違いが実際に残るか未再現。 | 現行mainのbinding/karte両schemaを実行検証し、残存すれば最初の信頼検査で明確に拒否させる。 |
| [Issue #679「agy-delegate: 会話記録・結果ファイルの確定と CLI 返却の一致（二重故障の窓）」](https://github.com/hiratashinnya/review-system/issues/679) | 確認済 | 本文は PR #627 がopen/draftかつコードがheadにしか無いとするが、2026-10-30にmerged。二重故障時の保存結果/CLI返却不一致は独立の未解決AC。 | 前提をmain統合済みへ直し、実I/O再現と失敗時の原子的確定契約を別途検証。 |
| [Issue #578「harness と dsv2 の既存テストコードを tests/道具名/ へ移設する」](https://github.com/hiratashinnya/review-system/issues/578) | 確認済 | Blocker #542 と #538 はいずれもclosed。テストを tests/<tool>/ に移す計画の着手前提は満たされた。 | 今のtests/実ファイルを再棚卸しし、削除済みテストを対象外にした移設計画へ更新。 |
| [Issue #547「blocker_gate に非ブロッキング診断チャネルを追加し、機械可読レポートとして publish する」](https://github.com/hiratashinnya/review-system/issues/547) | 確認済 | Blocked by #461（CI診断の配送契約）はclosed。起票時の優先順位・実装着手待ちの前提を更新できる。 | 現行report配送契約と重複しないことを確認したうえで着手可否を決める。 |
| [Issue #576「PR #233 の公開前 remote 検証要件を #538／gitgate の複数ロール push 設計へ引き渡す」](https://github.com/hiratashinnya/review-system/issues/576) | 確認済 | #538はclosed。本文にCodex supervisorが今後撤去される予定とする記述が残る。旧PR #233の5つのremote公開前要件は引き渡し評価が必要。 | 現在のgitgate/publish実装と照合し5要件の採用/不採用/既実装を明記する。旧方式の復活はしない。 |
| [Issue #336「CodexにもContext-modeを導入する。」](https://github.com/hiratashinnya/review-system/issues/336) | 確認済 | 本文は40文字程度の短い記載と blocked-by#306 のみ。#306はclosedだが、Codex Context-mode導入の受入基準/実装範囲が未定義。 | 現行Codex/ctx環境に合わせて目的・Scope・ACを記入するか、既存Issueへ集約するか決定する。 |

## P3：古いベースラインや残論点の再測定

| Issue | 確度 | 調査結果 | 推奨 |
|---|---|---|---|
| [Issue #261「doc_system 完了までの処置計画（2026-07-28 棚卸し）— 取りまとめ」](https://github.com/hiratashinnya/review-system/issues/261) | 期限切れの基準値候補 | 2026-07-28のdoc-system-v2ダッシュボードのopen FNDやmaterialize件数、作業ブランチを基準値として記録。4ヶ月が経過し現mainの値は未再計測。 | dsv2 index/validate/drift/dashboardを再実行し、#253〜#256/#160〜#162の着手順と現在の母数を更新。履歴の数値は消さない。 |
| [Issue #127「doc_system自体のシステム構築完了」](https://github.com/hiratashinnya/review-system/issues/127) | 再計画要 | doc_system構築完了という旧上位目標のみの短いIssueで、長期間未更新。詳細AC・現行進捗は本文上確認できない。 | #261とdoc-system-v2現行計画の責務重複・進捗を照合し、親/完了条件を明記する。 |
| [Issue #128「review_systemのドキュメントをdoc_system対応フォーマットに変更」](https://github.com/hiratashinnya/review-system/issues/128) | 再計画要 | review_system文書のdoc_system形式化という旧上位目標のみの短いIssue。#835はharness中心でreview_system製品本体を対象外とするため単純重複ではない。 | doc-system-v2の現行schemaに適合させる対象とACを再定義する。 |
| [Issue #333「FND「検査対象探索の欠陥」と「ミラー未同期」を1件に統合すべきか（双方 ERROR・同じ下流損害）」](https://github.com/hiratashinnya/review-system/issues/333) | 再確認要 | FND 2件の重複判断はPR #326の古い状態に基づく。本文自身も#406/#407の導入で事実が変わった可能性を注記している。 | 最新FND原本・現在のmirror同期を読み、2件の機序分離がなお成立するか確かめる。 |
| [Issue #832「improvement(triage): triager が reviewer の到達経路・前提脅威の根拠を独立評価し、棄却候補を理由コード付きで owner-review に集約提示する」](https://github.com/hiratashinnya/review-system/issues/832) | 一部依存解消 | reviewer根拠欄の#830はclosed。一方triager本体の#783/PR #816は進行中で、本Issue全体の着手条件はまだ一部残る。 | #830完了を反映し、#783/PR #816の統合とschema契約を待つ範囲のみ残す。 |

## 対処不要または誤検出（Openのまま妥当を含む）

| Issue | 現時点の判断 |
|---|---|
| [Issue #652「#371 導入後の工程分離・新ロール権限・adviserを初回実dispatchで検証する」](https://github.com/hiratashinnya/review-system/issues/652) | 2026-11-18の本文追記で、pr-reviewerの限定Writeとingest-reviewer、Codex wrapperのread-only境界を分けて正しい検証期待値へ更新済み。 修正不要。実機ACは未実施のままであり、今回の棚卸しで合格判定しない。 |
| [Issue #804「karte: 診断（diagnosis）／メモ（note）の [x, y] が dumps→parse の往復で変質し、往復のたびに引用符が増える（K-02 分割前から存在・F-799-06）」](https://github.com/hiratashinnya/review-system/issues/804) | 現行IssueはClosed、ACチェック済み。以前のOpen候補から除外する。 追加処置なし。履歴の旧PR状態記述は書き換え不要。 |
| [Issue #811「coverage-html スキルの共通本文が計測対象を「review_system のみ」と書いており、.coveragerc の実際の source と食い違う」](https://github.com/hiratashinnya/review-system/issues/811) | 2026-11-17にClosed。過去の調査追記があるが、今回のOpen棚卸し対象ではない。 状態を尊重し、ACやクローズ理由の独立確認なく再オープンしない。 |
| [Issue #375「pr-reviewer の finding をファイルハンドオフ化する（主文脈のコンテキスト通過を止める）」](https://github.com/hiratashinnya/review-system/issues/375) | 本文は#800の実装後も残る子#801/#802/#803を正式に追跡し、旧ACは移設元の履歴と明示。PR #697への古い言及は全て現行状態断言とは限らない。 親Issueは維持。子Issueの証拠で完了判定し、誤検出のみで閉じない。 |
| [Issue #691「[トラッキング] レビュー指摘の自動仕分けとAdvisory中央台帳を導入する」](https://github.com/hiratashinnya/review-system/issues/691) | triage/advisory各Releaseの段階的実装を追跡する親。閉じた関連IssueやPR #696の記載は設計履歴を含み、機械抽出のみで陳腐化と断定できない。 親Issueは維持。子#783/#784/#785/#786/#832/#857等の実態を優先。 |
| [Issue #575「agy-delegate／silent-failure-diagnosis を .ai 正本構成で作り直し、agy 直接実行へ移行して agy-mcp-bridge を撤去する（PR #259・#260 の再実装）」](https://github.com/hiratashinnya/review-system/issues/575) | 2026-10-11に旧PR #259/#260の廃止と#605/#606/#607への移行を本文へ明示済み。#607の端末上撤去が未了。 Trackingを維持し、#607の完了後に閉鎖を判断。 |
| [Issue #606「agy-delegate を agy 直接実行ラッパーへ移行し、許可ルール検査と規範を整備する（#575 の子 S1）」](https://github.com/hiratashinnya/review-system/issues/606) | 実装PR #627はmergedだがIssueはOpen。ACの実測・運用確認はコードマージと別であり、機械的な自動Closeは不適切。 残ACと#607/関連Issueの実機証拠を確認してからクローズ判断。 |
| [Issue #607「agy-mcp-bridge を撤去する（MCP 登録と実体の削除・オーナー実行）（#575 の子 S3）」](https://github.com/hiratashinnya/review-system/issues/607) | bridge撤去はローカル環境のオーナー操作でありIssueはOpen。PRマージとは別の実行証拠と許可が必要。 勝手に削除/クローズしない。撤去後に#284/#290/#271の整理を判断。 |
| [Issue #310「refactor(issue-pipeline): 是正ループ ②-c をカルテ機構へ書き換え実害基準とエスカレーション条件を明文化する」](https://github.com/hiratashinnya/review-system/issues/310) | #308/#309がClosedなのは本文自身が『ブロック解消済み』と記しており、旧時点の誤認ではない。 ブロッカー文言だけで修正対象にしない。残ACの是非は別のコード検証。 |
| [Issue #5「設計⇔実装ドリフト対策：実装変更時に影響する設計書へ必ず反映する仕組みを考える」](https://github.com/hiratashinnya/review-system/issues/5) | review_system製品の設計・実装ドリフト対策。#835のharness ADR/PFD/DFD発掘は製品本体を明示的に対象外としている。 廃止/統合しない。doc-system-v2依存の現行状況だけ別途更新候補。 |
| [Issue #835「[Tracking / Architecture Discovery] 既存開発基盤のADR・PFD・DFDを発掘し、改修時のドリフトを防ぐ」](https://github.com/hiratashinnya/review-system/issues/835) | 新しいharnessの設計資産復元計画。#745の変更との差分追従を明示している。 計画を維持し、後続のmain差分に合わせて履歴を吸収する。 |

## クロスIssue・PRの検証根拠

- [PR #259「fix(agy-delegate): fail-close の判定条件を是正し WSL パス誤記述を訂正」](https://github.com/hiratashinnya/review-system/pull/259) と [PR #260「feat(skills): 静かな失敗の診断(A21)を共有リファレンスとして資産化」](https://github.com/hiratashinnya/review-system/pull/260) はClosed / **未マージ**。[PR #268「docs(review_system): PR#258 の Codex レビュー残指摘を反映（Q26 起票・A9 撤回・L3 印）」](https://github.com/hiratashinnya/review-system/pull/268) はMerged。#273/#290/#291の現行ゲートは旧PRのマージを待つため実行不能。
- [PR #697「feat: pr-reviewer が finding を本人で karte へ取り込めるようにする（#375・stacked 上段）」](https://github.com/hiratashinnya/review-system/pull/697)、[PR #696「refactor: karte の取り込み処理と通知トリガー検出を責務分割し baseline を縮小する（stacked 下段）」](https://github.com/hiratashinnya/review-system/pull/696)、[PR #799「[Maintainability K-02] karte/model.py の review・正規化・表示責務を分離（#747・設計のみ先行）」](https://github.com/hiratashinnya/review-system/pull/799)、[PR #627「agy-delegate を直接実行ラッパー＋.ai 正本構成へ移行する（#606・draft・AC 未達）」](https://github.com/hiratashinnya/review-system/pull/627) はMerged。#792/#793/#802/#803/#805/#810/#679の『未統合待ち』は不要。
- [PR #740「refactor: branch source の引数解析を分離」](https://github.com/hiratashinnya/review-system/pull/740)、[PR #741「整数引数の不正値を拒否契約へ変換する」](https://github.com/hiratashinnya/review-system/pull/741) はMerged。#745の既存状態記載は訂正要。
- [PR #850「fix(#614) karte check の診断担当外 finding を安全に除外」](https://github.com/hiratashinnya/review-system/pull/850) は #614 の修正を統合済み。#714 (4) の別個の検証は残る。
- #652は2026-11-18に現行権限へ更新済み。#804はClosed。#811もClosed。古いレポートのOpen候補に戻さない。

## 監査品質・限界

- すべてのIssue本文は取得して文字列走査し、各ファイルに状態、全文長、ACチェック数、参照Issue/PR、見出し、状態・依存の引用と暫定評価を記録した。原文は raw/issues-*.jsonl に全件保存した。
- 全PRの状態はRESTの /pulls?state=all 5ページから取得して照合。状態は取得時点のsnapshotであり、その後の更新は新たな監査が必要。
- 参照先Issueの状態を444件の母集団で照合した。『Closed Issueを参照した』ことだけでは陳腐化とはみなしていない。
- 重点候補はGitHubの現行本文を再取得し、現行mainのkarte/model.py、karte/README.md、.claude/rules/05-skills-agents.md、.ai/Individually-managed-lists.md、maintainability_lint/baseline.json等を再読した。
- **全コメントの全文・全ACの実行再現・全Issueが指す全コード行の再検証までは行っていない。** 未実測と解消済みを混同しない。保守性の44件はbaseline登録数でありCIのlive再実行値ではない。
- 計画・逐件メモ・原文・索引・重点判断をこのブランチに保存。Issue修正・PR作成・マージ・クローズは実施していない。

## 推奨実施順

1. #273/#290/#291と#284/#285の旧方針ゲートを、#575/#605/#606/#607に接続して再編する（所有者判断は残す）。
2. #745の現状44件と既マージPRを更新し、#859の決定に基づいて#752〜#756の削減・存続を整理。
3. #805・#714の現行ドキュメントを是正し、#802/#803/#810/#792/#793の着手待ちを取り去る。
4. #679/#578/#547/#576の前提を再基線化して着手可能分を解放。
5. #261系列と#336/#333は最新原本に照らして再計画（状態だけでクローズしない）。

## 保存形式

- PLAN.md: 調査順序と完了判定。
- memos/issue-XXXX.md: **444件・1 Issue 1ファイル**。
- raw/issues-YYYY-MM*.jsonl: **全Issue本文**（8期間別）／raw/pr-index.jsonl: 406 PR。
- raw/issue-status-index.jsonl、raw/index-part1〜3.jsonl: 関連先突合用の構造化索引。
- reports/INDEX.csv: 444 Issueの一行索引。reports/CROSSCHECK.md: 初回の横断抽出。spotchecks/: 重要候補の個別再判定。
