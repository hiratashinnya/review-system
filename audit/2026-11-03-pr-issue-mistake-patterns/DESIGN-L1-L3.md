# 長期対策 L1–L3：契約・復旧・コマンド安全性の実装仕様案

作成日2026-11-03 / ChatGPT (AI)。**未承認の設計提案**。Issue本文・ACへの変更は未実施。参照: [調査](README.md)・[L4–L6](DESIGN-L4-L6.md)・[Issue反映計画](ISSUE-HANDOFF-PLAN.md)。

## 共通の優先設計原則

- 正本を増やさない：工程成果物はissue_envelope、実行ライフサイクルは将来のAgentRun(#409)、worktree所有はissue_start/worktree_ledger.py、review findingはKarte、owner decisionはfeedback_ledger/既存判断記録、PR状態はGitHubとする。
- issue_envelopeの現在の形式は issue-envelope/v1.0。互換破壊を伴う仕様更新は版・consumer・テスト・移行を同一変更単位で扱う。未知fieldを黙って無視して成功としない。
- D0の正しい拒否は迂回しない。自動復旧と証拠保全を分離し、停止中に勝手な他経路実行を行わない。
- #371導入後のlive権限検証は#652が担当。全製品・全PFでテストしたと主張しない。
- #370の既決：merge前useの機械ゲートを**先回りして新設しない**。本レポートのclose gateはAgentRun・工程遷移のみ。owner手動mergeは維持する。
- 本レポートは凍結設計の提案であり、オーナー承認・既存Issue本文との照合を経て実装する。

## L1 工程間の「期待成果物グラフ」を検証する

### 対象と既存機構

- issue_envelope/schema.py：InvestigationReport/VerificationDesign/ChangePlan/TestDesignの型、phase、run_id、target_key、input_digest、snapshot_oid、input_refs、owner decision、AC網羅。
- issue_envelope/handoff.py：後段起動時のproducer/phase/Issue/run/target/digest/OID/refを信頼callerの期待値へ照合。
- issue_envelope/coverage.py：VDのACとCP work_unitsの網羅。
- issue_start/phase_dispatch.py と phase_review_receipts.py：owner承認、独立review、単一work unit、reviewed artifact digest、別contextの検査。
- #409のAgentRunは**OPENであり、存在しない完成実装を前提にしない**。本L1は#409のgraph/close仕様を補充するもの。

### データモデルと唯一の正本

新しいGraph永続ファイルは作らず、AgentRunの既存要求項目（予定）とissue_envelopeのcommitted成果物から**検証時に導出したDAG**を作る。

- 実行ノード：key=(repo, issue, run_id, phase, optional work_unit)。正本=AgentRun。
- 成果物ノード：key=(artifact_type, id, committed_path, sha256)。正本=issue_envelope/既存レビューcapture。
- 参照エッジ：
  - requires_run：後続runが先行run完了を要求
  - consumes_artifact：consumerが先行artifactのtype+digest+OIDを照合
  - reviewed_by：成果物に独立review receiptが対応
  - approval_ref：owner判断の既存記録を参照
  - verification_ref：テスト/検証結果への既存参照
  - karte_clearance_ref：対象Issue/run/round/headに束縛されたKarteの**status verdictとclose専用の評価結果**、disposition/承認policy/Advisory/申し送り証拠への参照。無進捗候補やcheck診断集合をclose用blocking集合と取り違えない。**AgentRunへKarte判断を複製した正本を保存しない**
- worktree owned_byはworktree ledgerの参照であり、AgentRunへ同じ所有状態を二重に書かない。
- **キャッシュは導出物**。古いDAGを永続化しない。真正のroot/sourceは信頼されたdispatch contextとcommitted artifactから得る。

### ゲートを置く位置と検査順序

1. dispatch前：trusted callerのrepo/Issue/target/role/snapshot OID/work unitを取り、対象ノードの要求先を導出。
2. 既存issue_envelope checkとvalidate_handoffでschema、必須値、canonical、木/DAG、STOP、未決判断、AC網羅を確認。
3. 既存phase_review_receiptsで独立reviewのstatus=clean・reviewed digest・別contextを照合。reviewerの自己申告receiptのみで通さない。
4. AgentRun側で依存runのcompleted、重複run key、同じkeyに異なるOID/ownerがないことを確認。transport timeoutは単独でfailed/completedにしない。
5. role permissionと実行PFの正規対応を確認。Codexは元callerの権限を超えず、origin/main profile pinを維持。
6. どれか不一致なら明確なreason code、expected/observed（機密なし）と関係ノード参照を返してSTOP。実行禁止。
7. 実行終了時に同じノードと成果物を再確認し、対象run/issue/round/headのKarte正本を再評価してからAgentRun close gateへ渡す。完了報告や単純な`status: open`件数だけではcompleted/denyを判断しない。

### AgentRun closeとKarte findingの用途別判定接続（F-733-04 / F-733-05）

- **判定入力と判定用途を分離**：Karteの検証済みreview原本・owner/disposition・policy/handoff/Advisory証拠を参照するが、`status`のverdict阻害集合、`escalate`の無進捗集合、`check`の診断要否集合、**AgentRun close専用の適格性**は用途別に導出する。原本が同一でも結果は異なり得る。AgentRunは判定を再実装せず、Karteの対象run/round/headに拘束された出力を消費する。詳細は[用途別判定表](DESIGN-L4-L6.md)。
- **#683の意図的非対称性を維持**：`status:open / harm:none / disposition:deferred / handoff検証済み`は3ラウンド無進捗の計数からだけ除外され、**`verdict:no-harm-only`とownerへの既存STOPは維持**。従って`escalate:no`や「申し送り検証済み」だけではclose不可。checkの診断要否も#614で明示承認されるまで既存動作を変えない。
- **closeに必要な条件**：Karteの検証済み`status_verdict`、close用途で有効な処置とowner判断、#409のhandoff/expected outputs/依存run・レビュー原本の検証がすべて成立すること。現行のstatusが`clean`を妨げる場合にowner専権のSTOPが未解決なら、無進捗の除外ではclose不可。#691の**正式Advisory**は、後続子Issueが承認された範囲でverdictやcloseへの効力を定義した後に限り非ブロック候補とする。
- **fail-close**：未分類・未承認のharm:real、owner判断未決、policy/Advisory/handoff参照不一致、別Issue/run/round/head、Karte不能はclose拒否。**#409の「未解消findingゼロ」を単純なopen件数でも`escalate`候補ゼロでも実装しない**。実装時は「close阻害findingなし＋承認済みverdict/owner条件成立」というACへの具体化を提案するが、現時点でIssueのowner決定や既存ACを変更しない。
- 全findingは`status:open`でも履歴として保持し、`deferred`やAdvisoryを機械的に`resolved`へ変換しない。#683はverdict変更をOut of scope、#614はcheck判断が未決という責務境界を尊重する。

### 結果値の提案

- valid：対象フェーズの全必須契約が成立。
- invalid：特定可能な不一致/欠落。
- indeterminate：API不能、観測不能、参照先正本の一部未確認。

invalid/indeterminateはdispatch不可。過剰denyを減らすため、**後段が必要としない環境のライブ未検証**を無条件でこのゲートに混ぜない。例えば#652のpostmerge製品実測が未完了でも、#371実装runの静的完了は既存の分離契約に従い報告可能。ただし実測完了とは言わない。

### 内部API案（新規確定APIではなく導出・テストのための構造）

~~~text
validate_phase_request(
  trusted_request: {repo, issue, run_id, phase, target_key, work_unit, snapshot_oid},
  committed_artifacts,
  review_receipts,
  agent_run_reader
) -> {verdict: valid|invalid|indeterminate, reasons: [{code, node, expected, observed}]}
~~~

信頼callerの期待値を入力成果物からコピーして作らず、existing boundaryが確立したexpectedを利用。validatorの実体は既存 issue_start/phase_dispatch.py 等へ統合する。新モジュールは責務分割に必要な場合だけ。

### 否定・異常試験

- L1-T1 producer・Issue・run・target・snapshot_oid・input_digest・artifact SHAの各1箇所改ざん→拒否。
- L1-T2 parent Issueとexecution Issueの取り違え、別work unit→拒否。
- L1-T3 VD clean reviewがCPと無関係、2a受理済みTDと2b入力が別digest→拒否。
- L1-T4 一つのACにwork unit欠落、未知のAC追加、DAG cycle→拒否。
- L1-T5 依存runがwaiting/stalled/failedである、transport timeoutのみをcompletedと誤認→拒否。
- L1-T6 reviewerとauthorのcontext同一、roleのpermission不足→拒否。
- L1-T7 postmerge live検証を別Issueへ明示した実装run→「実装条件充足」と「live未完了」を別判定。
- L1-T8 既存issue-envelope/v1.0 artifact読込互換、正常dispatch/独立reviewは通る。
- L1-T9 `status:open / harm:none / deferred / verified handoff`が3ラウンド継続→無進捗対象からは除外、**verdict=no-harm-only**維持。owner STOP未解除ならAgentRun close拒否。正式Advisoryは#691で承認された独立のverdict/owner条件が成立した場合に限りclose候補。
- L1-T10 未分類またはowner未決の`harm: real`がopen、Advisory未commit、GitHub転記失敗、別runのKarte evidence→close拒否。openの数だけで判定しない。
- L1-T11 Karte読取失敗・policy OID不一致・判定不能→close拒否。Karteに残る全findingの履歴は消さない。
- L1-T12 #683 verified handoffを無進捗計数から除外しただけで`check`診断不要や`verdict:clean`へ変化→契約違反。#614の既存判断境界を保持。
- L1-T13 verified handoffがhash不一致・宛先closed・検証不能となる→無進捗計数へ復帰。verdict/owner STOPとcloseの既存阻害は維持。
- L1-T14 同一Karteのstatus/check/escalate/close出力が用途別に異なるが同一の検証済み原本を参照→正規差として受理。別run/round/headの参照なら拒否。

### AC-L1

- [ ] Graphは既存の成果物とAgentRunから導出され、重複した永続正本を作らない。
- [ ] producer/Issue/run/phase/work unit/OID/digest/独立review/owner判断を具体的なtyped edgeで検査する。
- [ ] T1〜T14の正常・異常・版互換がテストされ、未知を成功扱いしない。
- [ ] AgentRun closeはKarteのverdict・owner判断・close専用判定を参照する。#683のverified harm:none/deferredは無進捗から除外しても`no-harm-only`/STOPを保持し、自動closeさせない。#691の正式Advisoryは承認済み契約の範囲に限り扱う。用途別の正負・証拠失効試験を固定する。
- [ ] AgentRun closeとworktree releaseとreview verdictの責務が分離され、cross-ledgerの参照だけに限定される。
- [ ] #652のpostmerge live未検証を実装合格と偽装せず、#370に反する先行mergeゲートを作らない。
- [ ] 既存issue_envelope check、unit/integration testsがGreen、schema版変更時は移行と全consumerを同期。

## L2 状態機械・安全な後始末・部分成功の原子的確定

### 所有と状態の正本

1. AgentRun(#409)がrun/phase状態の正本。queued/running/waiting/completed/failed/stalled、idempotency key、依存、最終検証結果とappend-only historyを担う。
2. issue_start/worktree_ledger.pyがworktree物理所有・状態の正本。既存のopen/running/stopped/release_pending/stale/released/abandoned等、**現行の状態語彙を尊重する**。
3. gitgate/worktree.pyが既存の唯一の物理解放経路。SubagentStopが直接git worktree removeすることは引き続き禁止。
4. karteはreview finding、agy_delegateの結果/会話記録はそれぞれの既存契約が正本。AgentRunが内容を二重に書かない。

### 実行状態とworktree状態の参照ルール

- AgentRun completedとworktree releasedは**独立**。run完了はhandoff/expected artifact検証済みを意味し、worktree解放は回収と所有確認後に成立する。
- 実行中のworktree（runningや停止未確定）を時間だけで消さない。heartbeat timeoutと停止した証拠は別物。
- worktreeにhandoffが無いSubagentStopイベントは、現行仕様では入れ子委譲中の一時停止の可能性があるためrunningのまま。勝手にstaleへ移さない。
- collect済みrelease_pendingでロックが外れた場合のみ、次dispatchで既存deferred releaseを行う。
- 5つの再発例（#559の未紐づけ、回収済み実体残留、非稼働なのにlive扱い、未push/固有commitなしbranch ref、git switch診断欠落）を個別トレースで固定。

### 状態回復アルゴリズム案（自動削除可能条件は厳格）

1. 起動前に既存ledger、git worktree list --porcelain、remote refs、保存済みhandoff/receiptを**同一snapshot**として収集する。git検査失敗は判定不能。
2. 物理pathは正規化・symlink拒否・repo内に限定し、既存gitgateのpath/ownership検証を利用。
3. 少なくとも一つの**信頼済みの終端根拠**（handoffが回収・digest検証済み、または対象workerの終了と対象runが一致する証拠）に基づいて解放候補を判定。PIDだけの一致、単なる時間超過、名前だけの一致では解放しない。
4. worktreeの未commit変更と未pushの固有commitを検査し、消えると復元不能な変更があれば破壊的削除をせずsafe recoveryへ。成果物は既存gitgateの回収契約で先に安全保存。
5. ledger lockの下で期待状態/OIDを再読しcompare-and-set。競合時は再評価し、既に完了した操作は冪等に同結果。
6. 検証済み候補だけをgitgate既存release verbへ渡す。新しいrm -rf経路を設けない。release_pending等の既存状態遷移を使う。
7. 判定不能な場合は明確な保留理由と所有情報を返して後続dispatchをdeny。危険なforce deleteで自動解決を偽装しない。

**ACと安全性の優先順**：#559の「手動介入なしで次dispatch」は、復旧可能と証明できる5つのケースに限定して満たす。信頼済みの死亡・無変更を証明できない未知状態にまで自動削除を要求しない。ここを無条件に広げるのはオーナー判断が必要。

### 永続結果とCLI返却の同値性（#679境界）

- 「処理成功」と「結果ファイルが書けた」を別々の真実にしない。**唯一の最終決定記録**（既存の結果正本）を定義し、callback/cleanup/同期等、成功/失敗しうる後処理をすべて最終決定**前**に行う。
- 書込みは既存の一時ファイル→fsync→atomic replace→parent dir同期を用いる。成否が確定しない場合は最終成功を返さず、durable状態の再読またはreconcileで回復する。
- 決定を永続化した後は、成否を変える処理を走らせない。非重要な通知だけをbest effortで後続できる。永続成功後に掃除失敗を理由にCLI failedへ覆さない。
- どうしても複数の独立ファイルを更新するなら、1ファイルのcommit markerを権威あるcommit pointとし、他は復旧可能な派生状態として起動時にreconcileする。二重故障（後処理失敗＋ロールバック失敗）で誤成功・誤失敗を作らない。
- ストレージが永続的に読み書き不能な極端な事態で「CLI出力と状態の同値性」を証明することはできない。その際はindeterminateとして操作を停止し、**同値性を保証できたとは報告しない**。#679は方式のオーナー決定をACに持つため、この推奨は未承認。

### 試験ハーネスとフォールトポイント

- 既存 tests/unit/test_worktree_ledger.py 等の命名は**実装時に確認**して利用。gitgate/worktree.pyのpublic verbとissue_start/gate_residue.pyを使い、実gitの隔離repositoryで結合試験。
- 故障注入地点：A handoff未生成、B handoff生成後/collect前、C collect済み/解放前、D解放成功/ledger更新前、E branch ref解放失敗、F lock取得不可、G worker遅延/通知遅延、H writer最終replace前/後、I終了応答消失、J再試行/同時close。
- どの試験も「成果物を消さない」「活性所有者を解放しない」「二重実行しない」「次dispatchへ復旧可能な事例は自動復旧」を同時assertする。
- 同じrunに2つのworkerが起動しないことをidempotency key、target_key、state lockで確認。transport wait timeoutだけでfailed/stalledへ遷移させない。
- 外部料金や製品内部状態に依存するケースはmock/統合/liveを区別して#652等へ引継ぐ。

### AC-L2

- [ ] #559の5経路に各1つ以上の故障注入試験と次dispatchの正例がある。
- [ ] 未紐づけ/非稼働誤認を検出しても、live不確定・未回収のworktreeは破壊されない。
- [ ] AgentRun状態とworktree所有を混ぜず、両台帳参照が一意・冪等。
- [ ] 並行close、timeout、重複dispatch、途中停止と再起動で活性workerを殺さず、欠落handoffをcompletedとしない。
- [ ] #679の永続結果/CLI返却整合方式がowner承認され、故障前後の試験で一致を検証する。再読不可時はindeterminateを明示。
- [ ] 既存gitgateの唯一の物理解放経路、D0、回収先・SHA、origin/main pinを維持する。

## L3 コマンド実行の安全性を「閉じた操作契約」で高める

### 保護対象の範囲

本repoの所有者方針は、AIによるmerge/auto-merge不可、role別push権限、危険/書込操作の制限、owner決定を尊重すること。現行 docs/tools/pr-merge-gate.md は、hookが静的command文字列検査であり**OSレベルのsandboxでも全shell構文の完全解析でもない**と明記する。

本案の目的は、任意の悪意を持つプログラムを完全隔離することではない。**誤操作・権限取り違え・意図せぬ間接操作の入口を減らす**。無制限shell実行を正規表現で完全解析する方針は採らない。

### 変更の単位

- 既存の安全重要verb（gitgate new-branch/adopt/commit/push/release、GitHub merge禁止、role権限付き操作）を対象とし、これらの正規入口はすでに明示argvと引数検査を持つので再利用する。
- 各verbの**許可された操作意味**を小さな仕様表として記録。例：operation_id、role、argv_schema、repo/target、認可されたbranch/ref/実体の所有、side_effect、fail_policy、元の呼出者。
- コマンド実行口のガードは既存agent_command_gateとPF hookへ残す。新たな万能shell parser・第二のpermission engineは作らない。
- 既存の静的検査では判定不能なshell variable、alias、スクリプト内部、ネストした文字列などは、許可する理由と検査先がない限り**安全重要操作に対して拒否**。一般のread-only操作全体を禁止するよう拡大しない。
- ownerの手動mergeはPF外の正規操作。AIのmerge denyをowner側操作へ波及させない。
- 相対cwdやRTK wrapperの表面表記に依存せず、正規verbでは**実操作対象**を解決して検査。branch/OID、worktree ownerを対象にする。

### 正規operation契約例（設計データ案、現行APIではない）

~~~json
{
  "operation_id": "gitgate.push-work",
  "actor_role": "issue-implementer",
  "repo": "owner/repo",
  "branch": "agent/issue-123-example",
  "target_oid": "<trusted-oid>",
  "side_effect": "remote_branch_update",
  "policy": "allow_when_owned_and_non_force",
  "approval_ref": "<trusted-dispatch-binding>"
}
~~~

実装では**ユーザー提供JSONを信用しない**。actor_role、repo、OID、owner承認済みwork unitはtrusted dispatcher/既存bindingから導出。コマンド文字列の自己申告を認可元にしない。正規化できない形はreason付きdenyとするが、通常の安全なread-only入力のallowケースをS3で継続固定する。

### 実装ステップ

1. 各hookの現在のoperation/role検査・ネイティブルール・未カバー形式を表にする。既存S3の対照fixtureをベースラインに使う。
2. Git writeとGitHubの高影響操作に限り、**信頼できる構造化verbの入口**でtarget/owner/OID/roleを検査する。一般shellの静的分類は既存のbest-effort防護として維持する。
3. 高影響操作は、必要な権限を持つ既存wrapperがある場合、直接shell表現からそのwrapperの利用へ誘導する。ただし無断の一括deny追加はせず、allowセットをS3で比較する。
4. GitHub REST/GraphQLの動的に読めない危険操作は、文字列だけで安全に分類できたと主張しない。危険性のある入力はdeny/ownerへの適切な停止。自己承認トークンの導入を禁じる。
5. CI+製品実機で、ローカルhook判断と実際のhost permissionが矛盾しないことを確認。ライブテストはS6のレシピへ委譲。

### モデル化するテスト集合

- L3-T1 権限付き正規verbは所有OID・branch・worktree・roleが一致すると許可、1要素でも不一致なら拒否。
- L3-T2 same operationを別のcwd・RTK wrapperにしても（正規入口の検証が可能な範囲で）同一判定。
- L3-T3 read-only roleでpush、AI merge、強制push、勝手なbranch削除→拒否。
- L3-T4 安全なPR view/diff、対象ファイルread、通常のCIコマンド→allow。過剰denyを新設しない。
- L3-T5 shell variable等の非解析可能ケースは保証範囲外/拒否を明記。無理な文字列parserでallowを捏造しない。
- L3-T6 別role/agentへの委譲で権限を昇格できず、origin roleのbindingが有効な場合のみ。
- L3-T7 mock hookが通っても実host権限の期待拒否が起きるかは別liveケースとして証拠を残す。
- L3-T8 旧正常コマンドを変換した後の回帰と、PF間の意図しない違いの不在を確認。

### AC-L3

- [ ] 安全重要verbの対象/actor/side effect/allow/deny/unknownを一意に定義した表がある。
- [ ] 構造化入口のtrusted bindingと実操作先が合致しない操作を拒否する。
- [ ] 少なくともT1〜T8の対照試験で危険操作の誤許可と正常操作の過剰拒否を両方向で測る。
- [ ] 現行hookの静的文字列検査の限界を隠さず、OS-level enforcement/悪意あるプロセス防御を達成したと主張しない。
- [ ] 第二のshell parser/permission台帳を作らず、existing gitgate、agent_command_gate、PF native permissionを再利用する。
- [ ] 製品経路での誤操作防止はS6のlive証拠を付す。未検証PFは未保証として残す。

## 実装責務と依存の境界

L1のAgentRun本体は#409、既存工程artifactは#371（CLOSED）の実装を再利用。L2の既知残留是正は#559、一般故障パターンは#699、結果/返却問題は#679で扱う。L3は新規独立成果に相当する場合のみ新Issue候補であり、#699は共通の失敗・冪等性契約テスト部分に限定する。#370のmergeゲート先行設置の不承認を覆す設計にはしない。
