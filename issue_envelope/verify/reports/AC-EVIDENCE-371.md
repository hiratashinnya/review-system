# #371 全27ACの実施証拠監査（Codex AI）

監査日: 2026-10-17。本表は開始baseに対する履歴であり、後追い差分のCI成功や#537受領を先取りしない。

対象main exact OID: `418807f93967b1c2de056425ca035c63f1a62a06`（PR #650 mergeCommit）。作業treeのfeature差分は採用せずgit showの同OIDを使用。

結論: **全充足ではない。AC18はpartial**。実製品liveを要するAC13/19/20/24は未実測だが、本文の既決の運用検証分離に従う#652起票・native親#368を確認したためexplicitly-delegatedと判定する。これはlive成功の判定ではない。

分類はACの観測対象に合わせる。fulfilledは現mainの契約/実装/既存CI証拠の充足であり、別記するlive経路の成功認定ではない。partialは現closeに必要な成果が一部不足。unknownは十分な証拠なし（今回の個別AC分類では該当なし）。

## AC原文と判定

### AC01 — fulfilled

> 8ロール（`issue-investigator`/`ac-designer`/`change-planner`/`plan-reviewer`/`test-writer`/
>   `issue-implementer`/`pr-reviewer`/`adviser`）について責務、禁止事項、入力、artifact、STOP、チャット戻り値が
>   定義されている。

共通creation-stage-contract、8 role別 .ai/agents/*.md、Claude wrapper。各6要素を契約として明記。

### AC02 — fulfilled

> `ac-designer`／`change-planner`／`test-writer`が全Issueで必須となり、検証設計（1a/2a）と本体（1b/2b）が
>   別コンテキストである。

issue-pipeline工程順、phase_dispatch.REQUIRED_REVIEWS、phase_review_receiptsのproducer/review context分離。live結果はAC13/#652へ分離。

### AC03 — fulfilled

> `plan-reviewer`が全Issueで無条件に起動し、1a単独→1b（1a↔1b整合）の順で別レビューを行う。

plan-reviewer.md、phase_dispatchが1bへverification_designのclean receiptを要求し、phase_review_receiptsが別contextを要求。

### AC04 — fulfilled

> `pr-reviewer`が2a（`TestDesign`）単独→2b（PR）の順で別レビューを行う（本改訂で新設した責務）。

pr-reviewer.mdの2a独立契約、phase_dispatchの2b prerequisite/test_design receipt照合。既存PR review責務を維持。

### AC05 — fulfilled

> `PlanReview`のAC検査が4点構造化チェックリスト（テスト容易性/曖昧さ/測定可能な閾値/既存決定との矛盾）を
>   持つ。

plan-reviewer.md:9の4項目。AC自体のquality reviewをtraceと区別。

### AC06 — fulfilled

> investigationの起動判定が機械可読で、起動・省略理由がartifactへ残る。

schema.pyのInvestigationReport investigation_required/reason、model.pyの0/1検査、共通契約の起動・省略記録。実測は#652低/中ケース。

### AC07 — fulfilled

> `issue-implementer`が承認済みplan ID/digestと単一work unitだけを受け、計画外判断が必要ならSTOPする。

issue_envelope/handoff.py plan/digest単一unit、phase_dispatchのwork_unit照合、issue-implementerの計画外STOP契約。

### AC08 — fulfilled

> artifactの欠落、producer/Issue/digest/OID不一致、stale、STOP、未決owner decision、AC未対応をfail-closeする。

handoff.py、phase_dispatch.py、phase_review_receipts.py、repository_artifacts/committed_artifact境界。欠落/不一致/STOP/ACの機械契約・既存negative CI。

### AC09 — fulfilled

> 各ロールのBloom分類とPF写像が追跡可能である。

issue-pipeline Bloom表、各PF wrapperとmodel_policy契約。具体実使用モデルの実測は#652へ明示分離。

### AC10 — fulfilled

> `ac-designer`/`change-planner`/`test-writer`/`issue-implementer`にpush権限、`plan-reviewer`/`pr-reviewer`に
>   push権限が無いことが機械的に強制されている。

phase_role_permissions.pyがWRITE_ROLESへgitgate commit/pushを限定。readonlyには読取verbsのみ。既存PF hookへ接続。live各role拒否はAC20/#652。

### AC11 — fulfilled

> `ChangePlan`/`VerificationDesign`が`tmp/_handoff/`を経由せず、`gitgate new-branch`/`adopt-branch`で
>   worktreeへ直接commit+pushされる。

共通契約とFBK-20261017-工程別worktreeへ同一branchを継承するにより、作者自身の直接commit/push・new/adopt継承を定義。旧同一worktreeはowner改訂済み。live継承確認は#652。

### AC12 — fulfilled

> 検証エビデンスの`ST`/`IT`/`UT`各レベルでTD→TC→TRの鎖が揃っている（`ST-TC`/`IT-TC`/`UT-TD`の欠落がない）。

issue_envelope/verify/designs/{ST,IT,UT}-TD-371-envelope.mdがTCパスと各TRを参照。ST/IT-TCはtests/issue_envelope/test_acceptance.py、test_graph.py/test_trace.pyに実体。TRはlocal契約検証と明示。

### AC13 — explicitly-delegated

> 低リスク経路 `1a/1b→2a/2b`、中リスク経路 `investigation→1a/1b→2a/2b`、高リスク経路（モデル階層引き上げ）を
>   実測している。

未実測。#371本文の運用検証分離契約に基づき#652（open）の低/中/高ケースへ移管。2026-10-17 fresh /652/parentで#368を確認。#652実測完了とは扱わない。

### AC14 — fulfilled

> `VerificationDesign`/`ChangePlan`のトレサビ（`ref=`宣言駆動の共通アダプタ）が動作し、孤立・矛盾を検出する。

schema.py Field(ref=)、query/check、harness_trace共通adapter。test_traceの任意名ref/孤立検出・8ノードCP/VD復元、test_graphの矛盾/cycle検査。

### AC15 — fulfilled

> #409へ将来渡すrun/phase/expected outputの契約が明記され、二重ledgerを作らない。#409実装完了を本Issueのclose条件にしない。#310／#409とのphase・close条件の差分が接続仕様に反映されている。

issue_envelope/README末尾前のrun/phase/dependency/next_expected_artifact、creation-stage-contract返却節、downstream-impact-371 #310/#409欄。#409実装はclose前提にせず別ledgerなし。

### AC16 — fulfilled

> `python3 -m asset_parity check`、`maintainability_lint check`、`model_policy check`、生成物同期検査、対象のunittest／CIが通る。harness新配置のテストもCI・lintの対象になる。

r6既存CI check-runsはbe02f688（unittest/build/typecheck/feedback-ledger/check成功、deploy skip）。be02f688・final head680147e2・merged418807のtreeは全てa35b264235bdf6456c693243d5b80dd6721f1d19で同一。対象validation/asset_parity等の既存証跡と接続。新たなローカルテスト未実行。

### AC17 — fulfilled

> CP／VDのルート・中間・葉が同じ型で読み書きでき、包含関係と実行順DAGを別々に検証する。単一対象と複数対象／中間グループの例で全体復元・参照検査を確認する。

共通SPECSとgraph/store、test_graph.py/test_trace.pyの単一対象、中間group、複数対象CP/VD、canonical roundtrip、独立DAG検査。

### AC18 — partial

> ADRとowner decisionの記録先が#540の境界に従う。#371担当文脈で`LEDGER_SPEC`の欠落なし確認を行い、結果を#537へ渡す（#537全体の完了待ちではない）。

ADR/owner境界は記述あり。LEDGER-SPEC-371は確認結果を作成したが新role列挙不要という記述は実コードと不整合（別ledger監査）。末尾で#537投稿未実施と明記。fresh #537最新comment6214228158も#371確認が未受領と明記。#652はこのACを受けていない。

### AC19 — explicitly-delegated

> 同一ロール・同一work unitを別の実行先へ移しても、責務、禁止事項、成果物、承認点が維持される。

契約・profile/入力束縛は実装済みだが実実行先を移した維持確認は未実測。#652の著作者/readonly/工程継承ケースが引継ぎ。agyは未成立のままdisabledを維持。

### AC20 — explicitly-delegated

> 実行先ごとに許可操作と拒否操作を実起動で確認し、元ロールを超える権限行使が拒否される。

各backend/roleの実起動許可・拒否は未実測。#652の著作者/readonly/共通権限ケースで分離。unit/mock成功は代替しないと明記。

### AC21 — fulfilled

> 読み取り専用ロールの編集・push、当事者のreview台帳操作、全AIのmerge、任意再委譲が委譲経路でも許可されない。#608の削除・移動・baseline更新のSTOPも維持する。

共通creation-stage-contract権限節・phase_role_permissions/PF hook/profileが拒否契約を保持。製品live否定ケースは#652へ分離し未実測を成功扱いしていない。

### AC22 — fulfilled

> agy経路は#606／#628の成果到達と本Issueのロール別実測が揃うまで有効化されない。Codexは既存経路の検証結果を新ロールの検証成功に代用しない。

共通契約・issue-pipeline・implementation-boundaries-371・#652 OOSが#606/#628とrole実測未成立時のagy無効を明記。既存成功標本の新role転用を禁止。

### AC23 — fulfilled

> 既存ロールの横展開確認（#631）、#632／PR #633の導入状況に応じた起票実行の境界、短い返却と永続artifactの整合を確認する。

downstream-impact-371が#631横展開・#632導入済み起票専用境界・PF薄wrapper/非移植・短い返却と永続artifact契約を確認。Project書込失敗も未完了と区別。

### AC24 — explicitly-delegated

> 低ティア実行者から上位モデルへの相談と、同じ担当ロールへの回答返却・検証を実測する。

低tier→上位adviser→同じ担当への回答返却/検証は製品経路未実測。#652 adviser正常系とモデル/費用記録へ移管。

### AC25 — fulfilled

> adviserの回答では必須レビュー、STOP、owner承認を迂回できない。

adviser/creation-stage-contract/issue-pipelineで助言は必須review/STOP/owner承認の代替不可。phase_dispatchはowner承認とclean receiptsを独立必須にし、助言captureは承認receiptを作らない。

### AC26 — fulfilled

> 相談失敗、部分出力、予算到達を成功扱いせず、証拠付きで主文脈へ戻せる。

codex_worktree_exec/adviser_capture.py AdviceCaptureErrorがfailed recordを保持しpartial/失敗/budget到達でcompleteを返さない。budget.pyの上限検査。live異常確認は#652。

### AC27 — fulfilled

> 相談の入力参照、モデル、回答、採否、検証結果、コストを追跡できる。

adviser_request/captureはorigin role/run/phase/unit/refs digest/OID/modelとtrusted使用量・費用を保持しadoption/reason/verification_resultをpendingから担当が記録する契約。実採否/検証は#652正常系。

## 本文・コメント・owner決定の補足

- fresh #371本文は27 AC、全commentは1件（5773669483、2026-09-22 AC品質指摘）。この指摘は現AC5とplan-reviewer無条件化へ反映済み。数値目標提案はowner決定ではなく、本文でも施策固有目標は未設定と明記する。
- 本文のowner確定2026-09-06の分離契約は、新機能の一回限りlive検証を別Issueへ移し、実装close条件を起票+relationとする。#652を#371のblocked-byにしない設計。fresh #652本文とnative parent endpointで#368を確認した。
- 同一worktreeからrole専用worktreeへ同一branch exact OID継承への変更は、mainにFBK-20261017のowner逐語決定があるため旧AC11を字面のまま違反としない。
- Scope/導入順は#370事例再分類と品質/追加dispatch cost計測を要求するが、導入後品質効果・観測窓・中間目標は未決/未実測。downstream-impact-371は未完了を明記し、#652は長期品質測定をOOSとして#368/#370へ残す。AC13/24をこの長期効果へ読み替えてはいない。
- 本監査はコード全体への新規脆弱性検査ではなく、ACと実施/受領証拠のread-only監査。新payload/再現コード/ローカルテストは作成・実行していない。

## 後追い是正と最終判定条件

新6ロールのv1.2対応と訂正報告は [LEDGER-SPEC-371.md](LEDGER-SPEC-371.md) を参照する。最終AC18の受領証拠は#537の#371担当コメントと後追いPR本文にある報告/head/OID/受領URLで確認する。文書作成のみでは充足としない。後追いheadのCIも完了後のPR checkから確認し、開始baseの既存CIを流用しない。

### 開始baseで検出した不足

AC18について、誤った「enum追加不要」を実スキーマへ整合する再点検結果へ直し、#371担当文脈で確認した結果を#537が受領できる形で引き渡す必要がある。単なる#537 close待ちや#652への包括先送りでは代替できない。#371 reopenと後追いPRの要否・処置は主文脈がownerへ判断を提示する。

## 証拠の固定点と再確認先

- 監査対象は [main exact OID 418807f9](https://github.com/hiratashinnya/review-system/tree/418807f93967b1c2de056425ca035c63f1a62a06)。各コード・契約パスはこのtreeを参照する。
- [#371本文とコメント](https://github.com/hiratashinnya/review-system/issues/371)、[PR #650](https://github.com/hiratashinnya/review-system/pull/650) のmergeCommitとcheckを照合した。
- [#537の監査時最新受領](https://github.com/hiratashinnya/review-system/issues/537#issuecomment-6214228158) は#540担当#648だけを記録していた。#371分の最終受領は後追いPR本文と#537の対応コメントで再確認する。
- [#652](https://github.com/hiratashinnya/review-system/issues/652) は2026-10-17時点open、native parentは#368。実測未完了を成功としない。
- AC16のCIはbe02f688に対する既存check-runsと、final head680147e2・merged418807のtree同一性を根拠とする。後追いPRの新headに対するCI結果は別に確認する。
- 監査原本の一時取得JSONや絶対ローカルpathは永続証拠の取得先とせず、上記OID・URL・本文で再確認できる形にした。監査時点のAC判定と、以後変化する受領/CI/live結果を混同しない。
