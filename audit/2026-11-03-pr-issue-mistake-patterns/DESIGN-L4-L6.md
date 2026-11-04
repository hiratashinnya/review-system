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
- evidence_identity：PR番号、event種別、event payload上のPR head SHA、実際にcheckout/testしたSHA（PR merge refならmerge SHA）、必要ならbase SHA、workflow run ID/attempt/job ID、completion、result
- verification_kind：static / unit / integration / live
- requirement：premerge_required / postmerge_oneoff / continuous
- status：pass / fail / pending / not_run / blocked / not_applicable
- reason/evidence：workflow URL、対象headの照合、未実測理由

Obligationは実際に必要な検査だけ導出。CIがskippedでも、変更面が対象外ならnot_applicableとして可。必要なのに起動せずskippedならnot_run、合格ではない。

### 検査アルゴリズム

1. 信頼済みbase/headの変更ファイル一覧を取得し、CIの各trigger（path filters）へ適用。GitHub APIで取得結果が不完全ならcompleteとはしない。
2. unitテストはPR常時起動の既存workflowで**そのPR headに紐づくrun**を確認する。`pull_request` eventのrunは既定のcheckoutでmerge-refをテストし得るので、head SHAとtested SHAの一致を直接要求しない。typechecked-filesは**実際のjobが読むリスト**を唯一の対象として使用し、削除・rename・警告隠蔽など「見かけ上のGreen」を区別する。
3. .ai/asset関連の差分は、既存 asset_parity/trees.py の関係とasset-parity.ymlのtrigger条件をテストで照合。trigger-onlyの .ai/** をscan対象だと偽らない。
4. pages_build等のPR成果物検査とmain上deployは別event、別目的。PRにdeploy権限を付けない。
5. 必須jobは**run ID/attemptとそのevent payload**でPR番号・event種別・`event.pull_request.head.sha=A`を現在のPR head=Aへ対応づけ、`GITHUB_REF=refs/pull/N/merge`の場合は実checkout/tested SHA=M（merge commit）を同runの証拠として保持する。**M≠Aでも正規のCI成功**であり、単一の`head_sha`欄がAと一致しないことだけで拒否しない。head更新A→Bでevent head=Aの旧runを拒否し、base更新後の検査対象/鮮度も確認する。job status=completed/conclusion=successの必要条件は別途検査。対応証拠を取得できない場合は`not_run`や`pass`でなく検証不能としてfail-close。
   - `pull_request`以外（workflow_dispatch等）ではevent種別に応じた実checkout SHAを明示し、別イベントの成功をPR headの成功に流用しない。参照: [GitHub Actions公式](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)。
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
- L4-T4a `pull_request` eventでhead=A・merge-tested=M（M≠A）・PR番号一致・run/job成功→正規のCIとして受理する。
- L4-T4b headをA→Bへ更新すると旧event head=A・tested=Mの成功ではBをpassにできない。別PR・event不一致やbase変更後の鮮度不明も拒否する。
- L4-T5 CIがskip/pending/失敗/未起動→それぞれ区別、必要なjobは合格としない。
- L4-T6 pages PR buildは検証するが、PRからの本番deployを要求しない。
- L4-T7 hookのunit/mock成功だが本番未発火→live obligationはnot_run/blocked。
- L4-T8 既存の全PR unittestやasset-parityを二重起動する新workflowを作っていない。

### AC-L4

- [ ] 検査が必要になる変更面と、実際のjob/対象・対象head・実行証跡を対応づけられる。
- [ ] `pull_request`のevent head=Aに由来するmerge-tested=M（M≠A）のsuccessを正しく受理し、A→B更新・別PR/別event・旧base・証拠不足をsuccessと誤認しない。
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
- triage完了時、正本review/triage/policyを検証してからKarteに原子的に反映する。**未処置harm:real／statusのowner STOP要否／escalateの無進捗を別々に検証**し、#513でowner承認された停止理由に限り全denyへ接続する。`escalate:no`だけでowner STOPを解除せず、`escalate:yes`だけで未承認の全tool停止を発動しない。
- triageを起動できない、失敗した、戻り証拠が不正なら後続phase不可とし、owner-reviewへ上げる。未仕分けをclean扱いしない。
- #513の停止解除経路は、ownerの回答が明示したfinding/decision/Issue/runを**信頼されたhookやowner制御のCLI**で記録・検証した後のみ開く。AIの通常のEdit/Bashや「回答したと自己申告する」方法では解除できない。
- owner専権判断であるにもかかわらず許可toolがほぼゼロであるため、post-tool hookでの信頼された記録かowner管理の外部解除手段を用意する。製品の回答payloadに本人性/一致性が確認できない場合、**自動解除せず外部owner承認経路へSTOP**。

この順序は#513の「全deny」と#691の「triage先行」を両立させる**オーナーへの推奨選択肢**であり、既存Issueの承認済み仕様を自動変更する決定ではない。#513の強制対象と例外/解除をownerが明示承認しなければ実装のpermission境界を変更しない。

### 既存Karteの判定経路へ結線

- status/check/escalate/AgentRun closeは**同じ原本findingと検証済みdisposition・owner/policy・handoff/Advisory証拠を入力に使うが、用途別の派生述語を使う**。#503の一元化は現行の共通判定基盤として維持し、#683の`escalate`専用除外をverdict/checkへ流用しない。派生述語はKarte側の一箇所に置き、各CLI commandやAgentRun内へコピーしない。
- findingを「元のreview原本に存在するが今回の再レビューで省略した」場合は解消扱いにしない。全件再掲の既存規定を維持。
- scope overrideをowner本人の明示決定と事前承認policy適用に分けて保持し、triagerがreviewerのscope申告を無記録で変更しない。
- Advisoryの正本は#691で指定した .ai/advisory/ledger/ADV-<YYYYMMDD>-<slug>.toml 。未commit/不正digest/参照欠落ではclean阻害から除外しない。owner判断ledgerとの二重登録を避ける。
- deferredは#683の検証済み転記を使用。GitHub Issueが存在することだけでなく、実際にfindingの必要情報が到達した証拠が必要。

### 検証済み入力を共有し、用途別に判定を導出する（F-733-05）

**共通の検証済み入力**は、review原本のfinding全件（id/status/harm/disposition/round）、run/Issue/head/digest、owner判断・policy版、#683 handoffの転記先Issue状態/内容hash/verified_at、#691 Advisoryのcommitted正本と検証結果とする。証拠は既存Karte/Review/owner判断の正本から読み、独立した判定台帳は作らない。**入力の単一性は、出力結果の同一性を意味しない**。

| 派生判定（単一のKarte実装へ集約） | 役割と適用境界 | `status:open / harm:none / disposition:deferred / handoff検証済み` の期待 |
|---|---|---|
| `verdict_blocking` / `status_verdict` | 現行 `karte status` の`needs_remediation`相当。#683では**変更禁止**。#691で承認済みAdvisoryに限り今後変更を審査 | 未解消がこのfindingだけなら **`no-harm-only`**。ownerへの既存STOPを維持 |
| `stall_candidates` / `escalate` | #683が検証済み`harm:none/deferred`を**3ラウンド無進捗計数と`render ★無進捗`からだけ除外**。残りのstalled/approach-saturationは既存判定 | 該当findingを無進捗から除外。ただし`escalate:no`は`status:clean`を意味しない |
| `diagnosis_required` / `check` | fixer診断網羅の現行契約を維持。#614の意図確認/owner決定、#691の承認済みAdvisoryを別審査。#683の除外を自動移植しない | **#614決定前は従来の診断要否を維持**。無進捗除外だけを理由に診断不要としない |
| `close_eligible` / AgentRun #409 | 検証済み`status_verdict`、その用途で有効な処置・owner決定、依存run/handoff/成果物検証に基づくclose専用判定。無進捗除外はclose免除ではない | **`no-harm-only`だけではclose不可**。既存STOPに対する有効なowner判断または将来承認済みの正規判定が別途必要 |
| `hard_stop_required` / #513 | 現行status/owner STOPと、#513で明示承認されたtool制御の対象・解除理由を使用。escalateの偽陽性抑制は別軸 | 無進捗から除外されても、owner判断が未決ならSTOP/解除条件はそのまま |

- #683で無進捗から除外できるhandoffにはsource findingの内容hash一致、転記先の本文/コメント読み戻し、Issueの実在・状態・close理由の確認、最終検証での再検証が必要。**転記先open＋証拠有効なら除外**、**closed / not plannedは必ず計数復帰**。hash変更・コメント削除/編集・API不能・転記先状態を取得できない場合も除外を無条件に維持せず、既存の無進捗計数へ戻す（fail-close）。**closed / completedは#683のQ3がオーナー未決**であり、A「計数復帰」（#683推奨）/ B「着地済みとして除外維持＋最終検証でclosed明示」のいずれも未承認。ここでどちらかを既定値に確定しない。Q3未決時のcompletedを`requires_owner_decision`として明示し、仕様上のpass/除外成功や確定したstall復帰と報告せず、採用決定まで後続の完了判定へ使わない。`status` verdictはhandoff無進捗除外とは独立して従来どおり`no-harm-only`を維持する。
- `closed`は一律の状態値ではない。判定入力は転記先Issue ID、GitHub上のstate/state_reason、closed_at、正本の検証証拠、Q3採用記録（必要時）とする。GitHubの値が`completed`か`not planned`か不明なら、推測でcompletedを認定せず検証不能側に倒す。**#683のQ3は明示owner決定・理由・証拠を保存した後にだけ仕様/ACの完成値として採用**し、先行して#409/#513のSTOP解除やcloseに結線しない。
- #691の`advisory`（harm:none・committed正本・owner承認policy等）は**別の処置種別**であり、#691の子Issueでownerが承認した場合に限りverdict/check/stall/closeへの効力を定義する。#683の`deferred`をAdvisoryと同じ「clean解除」とみなさない。
- #614の`check`側におけるharm:none/deferred/waived診断除外と主文脈担当fix-hereの扱いは**未決の独立した論点**。#614がその条件を確定するまでは、この設計を理由に既存`check`を緩和しない。#409は`escalate`用の集合や`check`用の集合をcloseへ転用しない。

### #409 close gateへ渡す検証済みclose専用判定（F-733-04 / F-733-05）

- **原本集合**：Karte内findingは`status:open`でも監査履歴をそのまま保持。`deferred`/Advisoryだからといって`resolved`へ書き換えない。
- **close専用出力**：対象Issue/run/round/headとKarteの`status_verdict`、処置証拠、owner承認、未決判断、#409固有のreview/handoff/expected outputs/依存run検証から`close_eligible`を導出。実装時の#409 AC「未解消findingゼロ」は**close阻害の未処置findingがゼロ、かつverdict/STOP/owner条件が通ったこと**へ具体化する案（Issueは未更新）。`status`の`blocking_findings`が空なら`verdict:clean`の一条件となるが、`stall_candidates`の空集合を同じ意味に使わない。
- **非対称性**：正式なAdvisoryは#691導入後の承認済み規範で許可されればclose候補。検証済み`harm:none/deferred`は#683により無進捗から除外されても**`verdict:no-harm-only`のままなので、それ単独でAgentRun closeを通さない**。正式な`harm:real/deferred`の扱いも#683を根拠に自動変更しない。
- **失敗側**：未分類/未承認`harm:real`、Advisoryのpolicy/正本不整合、別run/OID、必要なowner判断なし、Karte読取不能ならcloseを拒否する。**STOPの解除・no-harm-onlyの取り扱いはowner承認済みの仕様の範囲でのみ**適用。#409内に別のdisposition計算器や真偽正本を作らない。

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
| L5-T12 | 同一finding原本・同一の検証済み処置証拠を各commandに渡す | **用途別に異なる判定が可能**。verdict/check/stall/closeの入力同一性と出力独立性を検証 |
| L5-T13 | legacyKarteの旧値 | 互換読取、暗黙のadvisory変換なし |
| L5-T14 | 製品tool hookは存在するが発火していない | LIVE未検証扱い、保証しない |
| L5-T15 | openの正式Advisoryと、openのharm:none/verified deferredを別fixtureで入力 | Advisoryは#691承認済みのverdict/owner条件を満たす場合のみclose候補。**deferredは#683ではno-harm-onlyを維持し、owner判断なしにclose不可**。原findingは保持 |
| L5-T16 | 未分類/未承認の`harm: real`がopen、policy未承認、Advisory未commit、handoff未検証 | blockingまたは判定不能でAgentRun close不可 |
| L5-T17 | 同一run/round/headの正当な用途別差と、別run/round/OIDの混入 | **用途別差だけで拒否しない**。証拠参照不一致は拒否し、AgentRunの自己申告で除外できない |
| L5-T18 | `status:open / harm:none / deferred / verified handoff` が3連続roundで残存 | **verdict=no-harm-only、stallから除外、既存STOP維持**。checkは#614未決の現行契約、owner決定なしのAgentRun closeは拒否 |
| L5-T19 | T18のhandoff content_hash不一致・コメント削除/編集・ネットワーク/API検証失敗、宛先state取得不能 | 無進捗へ計数復帰（失敗理由は保持）。render ★無進捗も同一の対象集合。verdict/STOP/closeの無断解除なし |
| L5-T20 | T18で未修正findingの診断記録が無い | #614の決定前は既存`check`規定どおり。#683による除外で診断完了扱いしない |
| L5-T21 | #691でowner承認されたAdvisoryが正本/版検証済み、または参照無効 | 承認済みの範囲だけ用途別に非ブロック。失効すれば各用途で保守側判定へ戻す。deferredへ拡張しない |
| L5-T22 | verified deferredで`escalate:no`だが`verdict:no-harm-only`、owner未決 | STOP解除もAgentRun closeも行わない。`escalate:no`単独からclean/closeを推論しない |
| L5-T23 | T18の転記先`open`、hash/内容/状態が再検証済み | 無進捗計数から除外、verdictは`no-harm-only`維持。check/STOP/closeは別用途の既存条件 |
| L5-T24 | T18の転記先`closed` + `state_reason:not planned` | **必ず**無進捗計数に復帰、renderと同期。#683 Q3に依存しない |
| L5-T25 | T18の転記先`closed` + `state_reason:completed`、#683 Q3未決 | 結果は**`requires_owner_decision`**。A/Bのどちらも確定済みAC扱いせず、成功／自動STOP解除／AgentRun closeと報告しない |
| L5-T26 | T25で#683 Q3をownerがA採用 | `completed`も無進捗計数へ復帰。#683の決定refとともに試験する（現時点では条件付きfixture） |
| L5-T27 | T25で#683 Q3をownerがB採用 | `completed`は計数除外を維持し、最終検証へclosedの事実を明示。#683の決定refとともに試験する（現時点では条件付きfixture） |
| L5-T28 | Issue state_reasonが不明、hash不一致、API不能、別Issueのclose情報混入 | completed成功と推測せず、証拠不完全として除外を認定しない。verdict/owner STOPは別判定 |

### AC-L5

- [ ] immutable reviewer原本、独立triage、policy版、owner決定と保存済みKarteがrun/issue/round/OID/digestで一致する。
- [ ] fix_here/deferred/advisory/owner_reviewを上記優先順で判定し、未証明の任意改善が勝手にcleanにならない。
- [ ] #513のhard stopとtriage必要性の競合についてownerが採用順と正規例外を明示決定し、T8～T11を確認する。
- [ ] hard stopが発火した本来対象のAI toolはAskUserQuestion/todo以外denyされ、正規owner解除の前に再開できない。対象外セッションの過剰denyを検証する。
- [ ] #691/#683/#375/#409の正本を重複させず、Karte status/check/escalateとAgentRun closeが**同一の検証済み原本入力から用途別の派生述語**を計算する。#683の無進捗除外はverdict/STOP/check/closeを緩和しない。#614の診断規則はowner決定まで不変。
- [ ] 正式Advisoryは**承認済みのverdict/owner条件を満たした場合だけ**close候補、検証済みharm:none/deferredは無進捗除外でも`no-harm-only`/STOPを維持しowner決定なしのcloseを拒否する。T12/T15〜T28の非対称・Issue状態fixtureを含むT1〜T28と旧データ/実機未検証を区別する。
- [ ] #683のQ3の採否を先取りしない。openは検証済みなら除外、closed/not plannedは必ず復帰、closed/completedはowner判断まで`requires_owner_decision`。採用後にだけAまたはBの条件付き試験期待値を確定し、handoff失効/API不能の経路も別に検証する。

## L6 merge後混入率と施策の効果を別の軸で計測する

### 正本と互換条件

既存 defect_metrics のレポートv1（defect_metrics/definitions.py SCHEMA_VERSION=1）と、定義済みの基線・窓、派生Issueの72時間条件・表記正規化は**変更しない**。defect_metrics/README.md の基線再現と異常通知も引き続き成立させる。

本施策は、#370の4分類とS1–S6/L1–L5の施策効果を、**レポートv1とは別の補助分析**として追加する。収集窓の母集団や分母を変えて見かけの改善を作らない。

### ケース注釈の候補モデル

全4分類を単一列の排他enumに押し込まない。#370の分類4「safe default・機械gate・lint不足」は、最初の3分類と同時成立し得るため**2軸**とする。

- discoverability（#370の第1〜3分類に対応する主分類）：
  - missed_premerge：merge前に検出可能だったが未検出
  - known_retained_at_merge：**merge前に発見済みで、そのfinding/OOSが修正されずmerge時点に残った**。owner承認済みdeferred、承認済みwaived、未決残置をすべて含む（承認の有無は主分類に影響させない）
  - live_only：merge後実機で初めて観測可能
  - unknown：判断材料不足
- mechanism_gap（#370の第4分類に対応する独立軸）：safe_default_gate_lint / other / unknown。複数gapなら配列。第4分類は第1〜3分類と重なり得るため合計件数へ二重加算しない。
- **disposition_state（第2分類の独立した内訳）**：approved_deferred（有効な承認と検証済み転記あり）/ approved_waived（有効な明示owner判断あり）/ fix_here_incomplete（修正決定済みだが未完了）/ undecided（有効な処置方針なし）/ other_verified（証拠付きその他）/ unknown。必要なら制度上のpolicy版や判断refを保存し、名前だけのdeferredを承認済みとしない。
- 各ケースにreview時点のhead OID、merge時点のopen/処置証拠、owner判断またはpolicy参照、分類者・日時を保持する。**PR後に起票されたことだけではmissed_premergeと判定しない**。merge前に修正・検証されて残置していないfindingは第2分類に含めない。
- **発見・残置の事実と、残置が適正かは別問題**。`known_retained_at_merge`は承認済みdeferredを含めて数える一方、「不適切な残置の実害」はharm:realかつ `fix_here_incomplete`/`undecided` 等の検証済み非免除ケースだけを別指標で数える。approved_deferred/approved_waivedはこの不適切残置の分子へ含めない。unknownは安全側に判断保留とするが、根拠無しに違反件数へも0件へも算入しない。

新規候補の一度だけの分類入力は、監査用のversioned annotation（例 audit/cohorts/<period>/classifications.json）。これは*人間が判断した分類*の正本として1か所だけ使い、Issue/PRの事実・Karteのfinding・GitHub状態を複製した正本にしない。自動収集できる値は計測時にGitHub/既存Karteから導出する。

### 集計定義案

- **母集団**：UTC半開区間 [start,end) にmerged_atが含まれるsame-repo PR。既存metricと同じ正規化・収集上限チェックを使用。
- **新規派生Issue**：既存defect_metricsの72時間の派生関係をそのまま利用。72時間超の遅発事例は別の追跡分析へ置き、v1の分母/分子に混ぜない。
- **ケース単位**：欠陥起源が同じIssueを1ケースとし、同じIssueへの複数PR参照は既存のdedupeに従う。分類不能はunknownとして残す。
- **混入率補助**：対象コホートで、各discoverability群とmechanism_gapに該当するケースの件数、対象merged PR数、100PR当たり件数を併記（サンプルが小さい場合は件数優先）。第2分類は**承認済み/未承認を合わせた残置総数**と、`disposition_state`別件数・未承認/未完了のharm:real件数を並べる。主分類合計にgap件数を足さない。承認済みの申し送りを集計から消す処理はしない。
- **施策採用前後の比較**：導入日・対象変更クラス・PRリスク・観測窓を固定。対策導入の前後で、既存のISSUE_PER_PR、派生率、再発、誤deny、レビュー工数を併記。施策が重なると因果の断定をしない。
- **初期ログ**：S1/2の追加調査時間、S3の誤deny/誤allow、S4代表変異の検出、S5の未読/CI OID不一致、S6のlive未実測数。これを数値KPIにする承認は別途owner判断。
- **計測不能**：収集打切り・API失敗・日時曖昧・分類証拠無しはunknown/error。0件と混同しない。

### 算出・出力方式

- pure関数で既存defect_metrics.types.WindowとIssueRecord/PullRequestRecordを入力し、検証済みのcase annotationsをJOINする。元のreport v1 schemaとJSON writerを変更せず、補助レポートは別出力。
- 推奨ファイル案：defect_metrics/classification.py（正規化と分類の検証）、defect_metrics/cohort_analysis.py（集計）、tests/unit/test_defect_metrics_cohorts.py。具体的分割は100物理行原則に従う。新規の常設workflow追加は既存異常通知との重複を確認後に判断。
- 補助レポート：schema_version、repo、window、snapshot_at、source_hash、merged_prs、derived_issues、classified/unknown、counts_by_discoverability、counts_by_gap、**known_retained_by_disposition_state**、**harmful_retained_without_valid_disposition**、per_100_prs、missing_evidence、methodology_version。
- 集計結果は導出物であり、GitHubやKarteの正本ではない。保存・配信する場合も新しいowner判断台帳を作らない。

### 試験

- L6-T1 #370の第2分類：merge前発見済みで別Issueへ残置された2事例（有効なowner承認済みdeferred／未承認）をともにknown_retained_at_mergeへ分類。内訳はapproved_deferred=1、undecided=1、未承認実害件数=1とする。両方をmissedには分類しない。
- L6-T2 live運用でしか分からないcron間隔の事象はlive_only、CIだけの事象と区別。
- L6-T3 caseがmissed_premergeかつmechanism_gap=safe_default_gate_lintでも2度分母加算しない。
- L6-T4 同一Issueの複数PR参照、#N/owner/repo#N/URL形式、重複issueを正規化。
- L6-T5 timezone/UTC半開区間/72時間境界の前後、API収集不足はfail-close。
- L6-T6 report v1と基線照合の出力は完全互換。補助出力を有効にしてもv1の値を変えない。
- L6-T7 case分類のevidenceが無い・古いOID・unknown→採用率や適正処置件数を過大評価しない。
- L6-T8 改善後の誤deny率増加を別指標で検出し、単純な欠陥件数低下だけで成功判定しない。
- L6-T9 有効なowner承認済みwaivedでもmerge時点にopenで残ったfindingは第2分類へ含むが、処置未承認の違反件数には加えない。ownerがfix_hereを選んだのに修正未了ならfix_here_incompleteへ分類し、適正処置済みと偽らない。
- L6-T10 merge前に検証済みで修正完了したfindingは第2分類に入らない。

### AC-L6

- [ ] #370の4分類を発見・残置（第1〜3）とmechanism_gap（第4）の2軸で表現し、第2分類は承認済みdeferred/waivedと未決残置をともに数え、独立した`disposition_state`で処置適正性を区別する。
- [ ] 同一のmerge前発見済み残置の承認有/無fixtureで第2分類が2件、未承認実害が1件となることを確認する。unknownは0件に読み替えない。
- [ ] 既存defect_metrics v1のschema・分母・72時間・基線・異常通知を一切変えない。
- [ ] 1つの注釈正本に根拠リンク、分類者/日時/基準版を記録し、派生集計は再生成できる。
- [ ] T1〜T10、コホート再現試験、データ不足時の明示的失敗が通る。
- [ ] 施策の因果評価は実測の観測窓・ケース数・複数同時導入という限界を記載し、削減率を捏造しない。

## 既存Issueとの責務境界

L4の型・schema ratchetは#701、trace/orphan検査は#703、live実測は#652。L5のpolicy/triager/Advisoryは#691（非実装tracking）、停止機構は#513、レビュー原本は#375、run closeは#409、deferredのhandoffは#683。L6の品質分類・導入後評価は#370、既存メトリクスの実装は#488（CLOSED）。各施策の新規Issue化の可否と「ここまでが完了」は[Issue反映計画](ISSUE-HANDOFF-PLAN.md)で独立に扱う。
