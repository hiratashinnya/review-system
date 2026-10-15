# Issue #629 独立再ローカルレビュー（Codex、r2）

対象: base b72d94bd → 8fa8f70cd2081f1f07b7ad745be6d53a2e0cfdb7。
初回reviewer・是正担当とは別文脈で実施。オーナー承認のIssue限定運用例外による公開前レビューであり、PRは未公開。

## 1. 判定と確認範囲

clean（凍結code/docsのローカルレビュー）。F-629-01はresolved、新findingなし。実装のリスクは権限境界・共有台帳を扱うため高、是正の波及はbase adapter群に限定される。全unit実行中のため実装作業全体の完了・公開承認・PR CI合格・merge可能の判定ではない。

24ファイルの全diff1113行を、1–100、101–200、201–300、301–400、401–500、501–600、601–700、701–800、801–900、901–1000、1001–1100、1101–1113として切り詰め・欠番なく末尾まで読んだ。AGENTS.md、.ai/agents/pr-reviewer.md、初回r1 report、是正rationaleも確認した。既存base engine（start/continue/abort/commit/tests/snapshot/resolution/live/git）、authority/request/CLI/dispatch、canonical ledger検証・atomic locked writer・Claude resolve fallbackを本文で追跡した。

Copilotの認可は専用base_authorizationsに保存され、entriesとdispatch lifecycleを共有しない。通常writerはdocument全体を保存するため認可を失わない。base_recordsで両collectionのoperation予約CAS・pending publish fenceを維持する。authorized/revokedを使い、再登録は旧認可を残して失効させる。既存worktree_ledgerとmaintainability baselineの差分はない。

登録のclean/live OPEN same-repository PR/fresh fetch/exact OID、開始のrequest完全一致、repository/branch/workspace/sessionの束縛を確認した。固定merge --no-ff --no-commit、任意option/strategy不可、成功かつ非ゼロunittest、内容CAS、全2親/tree、予約競合、API不要abort/recovery、pending commit/push fenceは既存engineを共用する。既存Claude fixer-only、既存Codex/unknown platform拒否、両hookのCopilot登録全role拒否、raw merge/PR merge禁止は維持される。

新規production moduleはbase_copilot.pyが70行、base_records.pyが14行、stdlibのみ。policy 1.2、Copilot正本と生成instructions、方法比較と認可/dispatch分離rationaleは整合する。ローカル信頼操作者の認可をhost/role認証やsandboxとして説明していない。保存ログの生出力paddingは証跡として扱い、code/doc whitespaceの品質と混同しない。

F-629-01仮説の再確認として、一時Git fixtureだけを使う4ケースを手元で実行した。登録/pending/committed/aborted各段階の単一Claude候補diff成功、本物Claude running時ambiguous-running、dispatch writer後の認可/operation保持、再登録revoked、破損collectionの開始/登録/publish拒否を確認し、4 tests / 1.071s / OKとなった。これはローカル仮説再確認でありPRのテスト合格を示さない。

対象OIDの追加保存ログはtarget 50 tests / 72.548s / OK、maintainability violations=0 accepted_debt=94、asset_parity 0 MISSING（29既存heuristic staleness）、guidance_sync OK、time_fixture violations=0を本文末尾まで確認した。旧実装全unitはABORTED exit130であり成功扱いしていない。

レビュー時点では後続の全unit最終ログ・完成版TR/handoff/PR草稿・失敗setup生ログ2本・追跡証跡をまとめた最終commitの追加diffは最終確認の対象として残る。現時点のTRはfull_unit_pendingと明示されている。これら後続証跡だけの確認は公開前最終確認で実施可能。今回凍結OIDのdiffに未読範囲はない。code/docsを追加変更した場合は本cleanの対象外として再レビューが必要。

共有code編集、branch切替、commit/push、外部投稿は行っていない。書込は許可されたr2 reportとfindingsのみ。

## 2. 指摘レポート

### F-629-01
harm: real
harm_detail: Copilot 登録を使った clone で後続 Claude subagent の差分検出による worktree 束縛が ambiguous-running となり、既存の自動実行経路が利用できなくなる。
severity: major
scope: in
locus: [gitgate/base_copilot.py::register, gitgate/base_records.py::authorization_records, issue_start/worktree_ledger.py::resolve_worktree_for_agent]
summary: 旧実装の Copilot 認可と running dispatch の混同は専用 base_authorizations collection と authorized/revoked lifecycle への分離により是正された。
evidence: OID 8fa8f70c の全diffとcanonical writerを確認し、一時Git fixtureの登録/pending/committed/aborted、本物running拒否、dispatch更新時保存、再登録revoked、破損collection拒否を含む4仮説再確認ケースが1.071秒でOKだった。
expected: Copilot認可とoperation証跡を維持しながら、Claude dispatch がない場合の既存 worktree 差分束縛が Copilot entry の存在に左右されない。
recheck: python3 -m unittest -v tests.unit.test_base_copilot.CopilotIntegrationTests.test_claude_fallback_registered_pending_and_committed tests.unit.test_base_copilot.CopilotIntegrationTests.test_claude_fallback_after_abort tests.unit.test_base_copilot.CopilotIntegrationTests.test_reregistration_revokes_authorization_without_dispatch tests.unit.test_base_copilot.CopilotIntegrationTests.test_corrupt_authorization_collection_is_fail_closed
status: resolved
disposition: fix-here

## 3. 次の処置

主文脈はF-629-01 resolvedを既存disposition fix-hereのまま取り込み、後続の全unit結果と最終証跡差分を公開前に確認する。code/docsが凍結OIDから変わらないことを照合する。未解消findingはない。

## 4. Owner report / merge

PR未公開のためGitHub owner report/fresh blocker report/PR checksは実行対象がなく、未取得。ローカルcleanをGitHub承認・CI合格・push/PR公開承認として扱わない。公開前に完成結果をチャットでオーナーへ提示し、公開後のPR checksとfresh blocker reportを確認してからオーナーの手動merge判断へ渡す。reviewerはmergeを実行しない。
