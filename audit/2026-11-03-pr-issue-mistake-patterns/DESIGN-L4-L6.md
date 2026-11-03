# 長期対策 L4–L6：検証経路・finding処置・欠陥計測の実装仕様案

作成日 2026-11-03 / ChatGPT (AI)。提案段階、未承認。Issue本文への反映なし。前提: [調査](README.md)・[L1–L3](DESIGN-L1-L3.md)・[Issue反映計画](ISSUE-HANDOFF-PLAN.md)。

## L4 変更差分→検査→正規実行の保証範囲を連結する

### 現状の保証と新規対象を峻別

- .github/workflows/tests.yml：PRでunittest（現状のsource全件）を実行。Typecheckは同workflow内の別job。通常の単体テストのPR起動経路は既存。
- .github/typechecked-files.txt：clean scopeリスト。ファイル増減に対してpyrightチェック範囲を段階拡張（#701の責務）。
- .github/workflows/asset-parity.yml：.ai/**を含む発火条件が既に修正済み（#467 CLOSED）。tests/unit/test_asset_parity_ci_paths.pyが対応を検証。ここを再実装しない。
- #530 CLOSED：.ai/agents/pr-reviewer.mdに大差分の読了・未読時のSTOPが規定済み。
- #652 OPEN：製品経路の初回実測が未完了。静的CIやmockのGreenと取り違えない。

今回の長期成果は、**検査の必要性→実際の起動→対象head/OID→成功証拠**の連結を、特定の高影響検査について再現可能にすること。すべての変更があらゆるworkflowを起動する要求ではない。

### 検査範囲モデル

対象となる検査を1件のcheck obligationとして表現する（永続版を新設するか否かは既存workflow/manifestから導出して決める）。

- obligation_id：asset_parity / unittest / typecheck / pages_build / live_hook / live_dispatch 等
- trigger_source：何を変更したら検査が必要になるか（正本のsource glob）
- test_target：当該jobが実際に検査する入口/ファイル/公開経路
- evidence_identity：PR番号、head OID、workflow run ID/job ID、completion、result
- verification_kind：static / unit / integration / live
- requirement：premerge_required / postmerge_oneoff / continuous
- status：pass / fail / pending / not_run / blocked / not_applicable
- reason/evidence：workflow URL、対象headの照合、未実測理由

Obligationは実際に必要な検査だけ導出。CIがskippedでも、変更面が対象外ならnot_applicableとして可。必要なのに起動せずskippedならnot_run、合格ではない。

### 検査アルゴリズム

1. 信頼済みbase/headの変更ファイル一覧を取得し、CIの各trigger（path filters）へ適用。GitHub APIで取得結果が不完全ならcompleteとはしない。
2. unitテストはPR常時起動の既存workflowでheadに対するjobを確認する。typechecked-filesは**実際のjobが読むリスト**を唯一の対象として使用し、削除・rename・警告隠蔽など「見かけ上のGreen」を区別する。
3. .ai/asset関連の差分は、既存 asset_parity/trees.py の関係とasset-parity.ymlのtrigger条件をテストで照合。trigger-onlyの .ai/** をscan対象だと偽らない。
4. pages_build等のPR成果物検査とmain上deployは別event、別目的。PRにdeploy権限を付けない。
5. 必須jobが、**判定時のPR head OIDと対応すること**、jobのstatusがcompleted、conclusionがsuccessであることを確認。古いheadの成功を流用しない。
6. 製品実測が必要なケースはS6の証拠様式を参照。実機未実測をCIのsuccessで補完しない。
7. fail/pending/not_run/blockedは「検査済み完全」とは表示しない。PR reviewer/owner reportの既存表示へ必要な情報を渡す。#370の既決に反する先回りのmerge gate追加はしない。

### 変更候補

- tests/unit/test_asset_parity_ci_paths.py の既存検査を再利用。
- .github/workflows/tests.yml のtypecheck jobと .github/typechecked-files.txt の整合を#701の範囲で強化。既存のgreen対象をテスト削除で縮小させない。
- #703のtrace checkerが成果物→検証の必須リンクを確認する。新たな汎用CI manifestを先に作らない。
- #702のevent/log共通契約へworkflow run ID・reason・source OID・収集元を提供する。ただし外部テレメトリを有効化しない。
- #652等、製品live検証は別Issue。ここに常設の有料統合テストは作らない。

### 試験ケース

- L4-T1 PRで .ai/のみ変更→asset_parity workflowが起動する必要がある。以前の#467の復元変異でチェックが赤。
- L4-T2 asset-parityのscan rootが増えたのにworkflow triggerが漏れる→既存path contractテストが赤。
- L4-T3 pyright対象のclean fileをリストから削除してgreenにする改変→coverage ratchetが検出。
- L4-T4 対象head Aでjob成功後、PRをhead Bへ更新→Aの結果ではBをpassにできない。
- L4-T5 CIがskip/pending/失敗/未起動→それぞれ区別、必要なjobは合格としない。
- L4-T6 pages PR buildは検証するが、PRからの本番deployを要求しない。
- L4-T7 hookのunit/mock成功だが本番未発火→live obligationはnot_run/blocked。
- L4-T8 既存の全PR unittestやasset-parityを二重起動する新workflowを作っていない。

### AC-L4

- [ ] 検査が必要になる変更面と、実際のjob/対象・対象head・実行証跡を対応づけられる。
- [ ] 未起動/skip/pending/古いOIDをsuccessと誤認しない。
- [ ] #467/#530のCLOSED実装を再作成せず、回帰検出を保持する。
- [ ] #701のclean-scope ratchetと#703のtrace/orphan検査へ責務を分離し、無検査化による偽Greenを検出する。
- [ ] S6/#652の実機未検証を区別し、外部課金・secret送信・PRからのdeploy権限を増やさない。

## L5 review findingの検出→仕分け→処置→停止解除を閉じる

### 既存Issueの責務と不変条件

- #375：review原本のcapture/真正性。#691：finding-triager、owner事前承認ポリシー、Advisory唯一台帳、Karteとの接続。#513：機械STOP・オーナー解除。#409：AgentRunライフサイクル。#683：deferredのGitHub Issueへの検証付き申し送り。
- #723はCLOSED。実害判定の唯一の規範は .ai/skills/review-harm/SKILL.md 。triager/plan-reviewer/pr-reviewerが**同じ正本**を読み、コピー別定義を作らない。
- review原本は不変。triagerの判断とオーナーの決定は別のprovenanceを持つ。未検証のhandoff/advisoryや、未決のowner判断が**暗黙にcleanを生むことはない**。
- 本案はownerのmerge操作を制御する新hookを含まない（#370で条件付き後送りが確定済み）。

### 仕分けを決定する入力

Karte/reviewerのfindingに対し、独立triagerが以下を根拠に分類する。

- immutable review artifactのID/digest・reviewer・run/phase/issue/round/head OID
- finding ID/harm/scope/severity/locus/evidence/expected/recheck
- AC、合格済みVD/CP、current code、前後差分、既存OOS判断、owner既存policyの版
- 起因（当該PR退行、元からある未悪化、検証不能）と実害根拠
- 読み込んだharm SSoTの同一性（pathとdigest）
- GitHub Issueへの転記・Advisory台帳への保存の検証証拠（必要時）

### 状態と優先判定

動作段階を review_capture → triage_pending → triage_validated → disposition_verified → karte_verdict とする。**これは処理段階の概念であり新しい永続run ledgerではない**。各工程ID/digest/入力OIDを既存#375/#409のartifactへ束縛する。

分類の推奨優先順：

1. 重大な契約違反/AC未達/今回の退行は原則 fix_here。仕様追加・scope変更・owner専権が必要ならowner_review。
2. 修正前から存在し悪化せず、AC/必須契約を阻害しないminorで、**既存承認ポリシーが明示許可し、転記先Issueが検証できる場合のみ**deferred候補（#683）。単にscope:outであることは条件にしない。
3. harm:noneで、AC未達/今回退行/必須規則違反ではなく、Advisoryの正本を有効なOIDに保存・検証済みで、owner承認policyが認める場合のみadvisory。
4. 曖昧、証拠不足、policy版不一致、GitHub転記失敗、未保存Advisory、レビュー原本不一致は**owner_reviewまたはSTOP**。
5. waivedやowner overrideはtriagerが新規に決めない。本人の判断記録/override_refが有効な場合だけ既存Karteの処理に反映。
6. 現行Karteのharm:none deferred非ブロッキング化などを、#691の全体設計・owner明示承認なしに先行変更しない。

### STOPとtriageの循環依存を解く設計案

**重要な競合**：#513は停止時にAskUserQuestion/todo系以外のツールを全denyする。#691は未処置findingをtriagerへ渡す必要がある。review取り込み直後に#513が発動すると、Taskでtriagerを起動することさえできずデッドロックする。したがって黙ってどちらかを迂回しない。

推奨設計：

- triage前のreview結果は**不変のreview原本としてcapture**し、通常の実装/再レビュー/mergeへは進めない。専用のtriage_pendingを#409の工程ゲートで保護する。
- triagerの一回だけの起動は、review原本に束縛された**trusted dispatcher**が事前に承認した専用role/phaseとして行う。汎用Task・Bash等を「stop解除のため」として無制限にallowしない。
- triage完了時、正本review/triage/policyを検証してからKarteに原子的に反映し、**そこで未処置harm:real / escalateなら#513の全deny停止を発動**する。
- triageを起動できない、失敗した、戻り証拠が不正なら後続phase不可とし、owner-reviewへ上げる。未仕分けをclean扱いしない。
- #513の停止解除経路は、ownerの回答が明示したfinding/decision/Issue/runを**信頼されたhookやowner制御のCLI**で記録・検証した後のみ開く。AIの通常のEdit/Bashや「回答したと自己申告する」方法では解除できない。
- owner専権判断であるにもかかわらず許可toolがほぼゼロであるため、post-tool hookでの信頼された記録かowner管理の外部解除手段を用意する。製品の回答payloadに本人性/一致性が確認できない場合、**自動解除せず外部owner承認経路へSTOP**。

この順序は#513の「全deny」と#691の「triage先行」を両立させる**オーナーへの推奨選択肢**であり、既存Issueの承認済み仕様を自動変更する決定ではない。#513の強制対象と例外/解除をownerが明示承認しなければ実装のpermission境界を変更しない。

### 既存Karteの判定経路へ結線

- status/check/escalateは同じvalidated disposition predicateを共有する。#503の既存一元化を利用し、判断ロジックを各commandへコピーしない。
- findingを「元のreview原本に存在するが今回の再レビューで省略した」場合は解消扱いにしない。全件再掲の既存規定を維持。
- scope overrideをowner本人の明示決定と事前承認policy適用に分けて保持し、triagerがreviewerのscope申告を無記録で変更しない。
- Advisoryの正本は#691で指定した .ai/advisory/ledger/ADV-<YYYYMMDD>-<slug>.toml 。未commit/不正digest/参照欠落ではclean阻害から除外しない。owner判断ledgerとの二重登録を避ける。
- deferredは#683の検証済み転記を使用。GitHub Issueが存在することだけでなく、実際にfindingの必要情報が到達した証拠が必要。

### 試験表

| Case | 条件 | 期待 |
|---|---|---|
| L5-T1 | reviewer原本とtriager artifactのdigest不一致 | STOP |
| L5-T2 | 同じfindingに独立したtriagerを通さない/異なる版のharm規範を読む | STOP |
| L5-T3 | AC未達、owner判断なし | fix_here候補/owner_review。自動waived禁止 |
| L5-T4 | harm:none、承認policy、Advisory正本保存済み | advisory可能 |
| L5-T5 | T4のAdvisoryが未commit、ID衝突、policy未承認 | advisory不成立、clean不可 |
| L5-T6 | 既存minorのdeferredを希望するがGitHub転記失敗 | clean不可、owner_review |
| L5-T7 | scope:outかつharm:real | owner判断なしでclean不可 |
| L5-T8 | triage_pending中に実装/再レビューを要求 | 既存工程ゲートdeny、triage以外進行不可 |
| L5-T9 | #513 hard stop後にTask/Bash/Write/Edit | AskUserQuestion/todo以外をdeny（承認済み特例以外） |
| L5-T10 | 偽owner応答、別runの判断ref、古いOIDで解除 | deny維持 |
| L5-T11 | 正規owner承認記録とKarte検証が一致 | stop解除、後続phaseは別途再検証 |
| L5-T12 | status/check/escalateで同一finding集合 | 同じブロッカー判定 |
| L5-T13 | legacyKarteの旧値 | 互換読取、暗黙のadvisory変換なし |
| L5-T14 | 製品tool hookは存在するが発火していない | LIVE未検証扱い、保証しない |

### AC-L5

- [ ] immutable reviewer原本、独立triage、policy版、owner決定と保存済みKarteがrun/issue/round/OID/digestで一致する。
- [ ] fix_here/deferred/advisory/owner_reviewを上記優先順で判定し、未証明の任意改善が勝手にcleanにならない。
- [ ] #513のhard stopとtriage必要性の競合についてownerが採用順と正規例外を明示決定し、T8～T11を確認する。
- [ ] hard stopが発火した本来対象のAI toolはAskUserQuestion/todo以外denyされ、正規owner解除の前に再開できない。対象外セッションの過剰denyを検証する。
- [ ] #691/#683/#375/#409の正本を重複させず、Karte status/check/escalateの意味が一致する。
- [ ] T1〜T14の代表異常/正常、旧データ、実機の未検証を区別したテストがある。

## L6 merge後混入率と施策の効果を別の軸で計測する

### 正本と互換条件

既存 defect_metrics のレポートv1（defect_metrics/definitions.py SCHEMA_VERSION=1）と、定義済みの基線・窓、派生Issueの72時間条件・表記正規化は**変更しない**。defect_metrics/README.md の基線再現と異常通知も引き続き成立させる。

本施策は、#370の4分類とS1–S6/L1–L5の施策効果を、**レポートv1とは別の補助分析**として追加する。収集窓の母集団や分母を変えて見かけの改善を作らない。

### ケース注釈の候補モデル

全4分類を単一列の排他enumに押し込まない。#370の分類4「safe default・機械gate・lint不足」は、最初の3分類と同時成立し得るため**2軸**とする。

- discoverability（主分類）：
  - missed_premerge：merge前に検出可能で未検出
  - known_unresolved_at_merge：merge前に発見済みだが処置/owner判断が不足
  - live_only：merge後実機で初めて観測可能
  - unknown：判断材料不足
- mechanism_gap（独立軸）：safe_default_gate_lint / other / unknown。複数のgapを持つなら配列で表現する。
- 両軸とも evidence refs、review時点の対象OID、結論・判断主体・日時を持つ。**単にPR後に起票されたというだけではmissed_premergeへ分類しない**。
- 既に処置承認済みdeferred等は「未処置の実害」と数えない。確定処置でなかったものと分ける。

新規候補の一度だけの分類入力は、監査用のversioned annotation（例 audit/cohorts/<period>/classifications.json）。これは*人間が判断した分類*の正本として1か所だけ使い、Issue/PRの事実・Karteのfinding・GitHub状態を複製した正本にしない。自動収集できる値は計測時にGitHub/既存Karteから導出する。

### 集計定義案

- **母集団**：UTC半開区間 [start,end) にmerged_atが含まれるsame-repo PR。既存metricと同じ正規化・収集上限チェックを使用。
- **新規派生Issue**：既存defect_metricsの72時間の派生関係をそのまま利用。72時間超の遅発事例は別の追跡分析へ置き、v1の分母/分子に混ぜない。
- **ケース単位**：欠陥起源が同じIssueを1ケースとし、同じIssueへの複数PR参照は既存のdedupeに従う。分類不能はunknownとして残す。
- **混入率補助**：対象コホートで、各discoverability群とmechanism_gapに該当するケースの件数、対象merged PR数、100PR当たり件数を併記（サンプルが小さい場合は件数優先）。主分類の合計にgap件数を足さない。
- **施策採用前後の比較**：導入日・対象変更クラス・PRリスク・観測窓を固定。対策導入の前後で、既存のISSUE_PER_PR、派生率、再発、誤deny、レビュー工数を併記。施策が重なると因果の断定をしない。
- **初期ログ**：S1/2の追加調査時間、S3の誤deny/誤allow、S4代表変異の検出、S5の未読/CI OID不一致、S6のlive未実測数。これを数値KPIにする承認は別途owner判断。
- **計測不能**：収集打切り・API失敗・日時曖昧・分類証拠無しはunknown/error。0件と混同しない。

### 算出・出力方式

- pure関数で既存defect_metrics.types.WindowとIssueRecord/PullRequestRecordを入力し、検証済みのcase annotationsをJOINする。元のreport v1 schemaとJSON writerを変更せず、補助レポートは別出力。
- 推奨ファイル案：defect_metrics/classification.py（正規化と分類の検証）、defect_metrics/cohort_analysis.py（集計）、tests/unit/test_defect_metrics_cohorts.py。具体的分割は100物理行原則に従う。新規の常設workflow追加は既存異常通知との重複を確認後に判断。
- 補助レポート：schema_version、repo、window、snapshot_at、source_hash、merged_prs、derived_issues、classified/unknown、counts_by_discoverability、counts_by_gap、per_100_prs、missing_evidence、methodology_version。
- 集計結果は導出物であり、GitHubやKarteの正本ではない。保存・配信する場合も新しいowner判断台帳を作らない。

### 試験

- L6-T1 #370の指摘するpremerge発見済みIssueをmissedに分類しない。
- L6-T2 live運用でしか分からないcron間隔の事象はlive_only、CIだけの事象と区別。
- L6-T3 caseがmissed_premergeかつmechanism_gap=safe_default_gate_lintでも2度分母加算しない。
- L6-T4 同一Issueの複数PR参照、#N/owner/repo#N/URL形式、重複issueを正規化。
- L6-T5 timezone/UTC半開区間/72時間境界の前後、API収集不足はfail-close。
- L6-T6 report v1と基線照合の出力は完全互換。補助出力を有効にしてもv1の値を変えない。
- L6-T7 case分類のevidenceが無い・古いOID・unknown→採用率を過大評価しない。
- L6-T8 改善後の誤deny率増加を別指標で検出し、単純な欠陥件数低下だけで成功判定しない。

### AC-L6

- [ ] 4分類を重複可能な2軸で表現し、主分類のunknownを保持する。
- [ ] 既存defect_metrics v1のschema・分母・72時間・基線・異常通知を一切変えない。
- [ ] 1つの注釈正本に根拠リンク、分類者/日時/基準版を記録し、派生集計は再生成できる。
- [ ] T1〜T8、コホート再現試験、データ不足時の明示的失敗が通る。
- [ ] 施策の因果評価は実測の観測窓・ケース数・複数同時導入という限界を記載し、削減率を捏造しない。

## 既存Issueとの責務境界

L4の型・schema ratchetは#701、trace/orphan検査は#703、live実測は#652。L5のpolicy/triager/Advisoryは#691（非実装tracking）、停止機構は#513、レビュー原本は#375、run closeは#409、deferredのhandoffは#683。L6の品質分類・導入後評価は#370、既存メトリクスの実装は#488（CLOSED）。各施策の新規Issue化の可否と「ここまでが完了」は[Issue反映計画](ISSUE-HANDOFF-PLAN.md)で独立に扱う。
