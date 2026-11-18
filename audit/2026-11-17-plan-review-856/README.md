# Issue #856 — 1a/1b PlanReview 実例監査（第一弾、2026-11-17）

## 対象と判定の限界

本書は実例を根拠に **審査規範の修正可否**を検討する監査であり、reviewerの原本やKarte原本ではない。確認したのはGitHub上のIssue記述と履歴ブランチに保存されたVDである。1a/1bの各PlanReview原本、当時のIssue本文snapshot、レビューごとのKarteとオーナー判断の完全な履歴は取得できていない。未取得の根拠を推定で補わず、findingの正当性・誤指摘率・ラウンド増加の因果関係は**判定不能**とする。

原資料：
- [Issue #655（冒頭の1a round 2 / 3 / 7後のScope/AC改訂記録）](https://github.com/hiratashinnya/review-system/issues/655)
- [Issue #662（同一branchで1a是正できない実行経路障害）](https://github.com/hiratashinnya/review-system/issues/662)
- [Issue #663（ST/IT TCの実コード化の担当契約欠落）](https://github.com/hiratashinnya/review-system/issues/663)
- [Issue #371（PlanReview四観点・AC妥当性確認の由来）](https://github.com/hiratashinnya/review-system/issues/371)
- VD原本の保存パス：`verification_design/VD-655.toml`（`claude/issue-655-untracked-source-classification-r2` / `-r3` / `-r7` / `-r21`）。
- [後段PR #818（2bコードレビュー：工程違いのため1a/1bサンプルには算入しない）](https://github.com/hiratashinnya/review-system/pull/818)

## 観測事実と一対一照合

「finding」は発見・レビューの原本IDを意味する。OBSは本監査の観測IDであり、finding IDに置き換わらない。

| 観測 | 当時のfinding原本と基準 | 承認済み要求・判断の確認 | 是正・VD履歴 | 再レビュー・結論 |
| --- | --- | --- | --- | --- |
| OBS-655-A：1a round 2 後のST/IT TC担当とCI追加 | finding原本未取得。Issue本文はround 2後の追記を記録するが、当時の違反基準は未確定 | Issue本文にownerの「2aでtest-writerがST/IT TCを実コード化」の決定を記載。契約穴は別 Issue #663 | `VD-655.toml` r2→r3で`scope`に`.github/workflows`と`tests`、ST-TD`-16`とST-TC`-16-1`が増加（blob `db0c77f`→`7863df2`） | 該当findingの状態・recheck結果は未取得。既存要求の不足か新規要求かは判定不能 |
| OBS-655-B：1a round 3 後のClaude側coverage wrapper | finding原本未取得。Issue本文はround 3後の追記を記録 | wrapperをScope/ACに追記したことは確認可能、当時のowner承認逐語・snapshotは未取得 | `VD-655.toml` r3→r7で`.claude/skills/coverage-html`が`scope`に加わる（blob `7863df2`→`e033ed5`）。中間ラウンドの特定は未確認 | 正当な影響面の発見か工程外要求かは判定不能 |
| OBS-655-C：1a round 7 後の失敗test集合比較 | finding原本未取得。Issue本文はround 7後の追加と選択肢(i)の決定を記録 | Issue本文は同じinterpreter・commitで失敗集合一致のowner決定を記載。逐語の完全な来歴は未取得 | `VD-655.toml` r7→r21でST-TC-05/06/13等の枝番が増加（blob `e033ed5`→`15dc09b`）。変更理由をこのfindingのみに帰属させない | 個別findingの再掲・是正完了・ラウンド別件数は判定不能 |
| OBS-662：1a是正のbranch継続不可 | PlanReview findingではない。Issue #662は`ac-designer`の継続契約不足を記録 | 既存の初回new-branch、後続adopt契約が背景 | #655の枝が`-r2`、`-r3`…と増えた観測がIssue #662にある | **実行基盤障害**。レビュー観点による手戻りとして件数算入しない |
| OBS-371：AC妥当性検査の設計理由 | 当時の独立1a/1b PlanReview findingではなく、歴史的設計根拠 | `audit/2026-09-21-pipeline-redesign/README.md` にACの機械判定/一意/閾値/決定整合の不足を記録 | 四観点の追加理由が存在 | **レビューの正例ではない**。四観点を削除する根拠にはしない |

## 改善対象と守る境界

**実害を早期検出し得る事例（観測）**：#655 の対象にはsource/TCの無断混入・異runtime cacheなど保護すべき入力整合・実行時安全の欠陥があり、#371が指摘するAC検証可能性不足も後工程の欠陥見逃しにつながり得る。これらを「工程外」としてレビューから除外してはならない。ただし1a原本findingとの直接対応は未実証であり、実測済み成功件数は算定しない。

**手戻り要因として確認できるもの**：#662の同一branch是正経路の不備はレビュー観点とは別の実行障害。#655でreview後にScope/ACが増えたことは確定だが、そのうち不要な手戻りだった割合は判定不能。原因を「不合理なレビュー」に帰属させない。

**規範の改善**：`.ai/agents/plan-reviewer.md`で1a（何を検証するか）と1b（どう満たすか）を分け、既存の四観点とharm正本は維持。findingには当時の基準・到達経路・前回判断・新証拠との差分を明示させる。新規Scope/AC/方式を承認済み基準へ昇格させず、未決はSTOP。レビュー原本・triager・Karteの処置判定には触れない。

**初回の回帰範囲**：`tests/unit/test_plan_review_scope_856.py`は規範条項の欠落・工程境界の混同を機械的に検出する契約テストであり、実LLMのPlanReview正例/負例を採点するE2Eではない。レビュー原本に基づくfinding-level fixture、独立の第二案件と実レビューround追跡は**未完了**で、Issue #856のAC1/2/6を満たしたとは扱わない。

## 次の監査で必要な原本

1. #655の1a/1b全PlanReview原本（finding ID、evidence、reachability_path、threat_assumption、round、disposition）と当時のIssue本文/VD/CP/owner decision snapshotの対応。
2. #655とは異なる1a/1b実行案件の同じセット。
3. 改定前後の必要実害finding、未承認要求候補、同一根拠再指摘、owner未決STOPを含む正例・負例のreviewer実実行と再レビュー検証。適用後に同条件で指摘再発・owner判断・残欠陥を測る。


## クローズ済みPRまで遡った追加監査（2026-11-18）

以下は発掘済みの**実証レベルを異なるまま**載せた一覧である。原本を確認したものと、実施の証言だけがあるものを混ぜて件数を水増ししない。対象はマージ済み/クローズ済みPR #684・#708・#731・#809・#650・#695、PR #847・#846と関連Issue。事例データの正本は [cases.json](cases.json)（レビュー原本や新たな合格判定器ではない）。

### 監査母集団・証拠の強度

| 事例 | 分類と証拠 | 証拠として言えること／言えないこと |
| --- | --- | --- |
| Issue #655：工程1a | [Issue #655](https://github.com/hiratashinnya/review-system/issues/655)・[Issue #662](https://github.com/hiratashinnya/review-system/issues/662)、[PR #684](https://github.com/hiratashinnya/review-system/pull/684)、[PR #708](https://github.com/hiratashinnya/review-system/pull/708) | **実1aの部分証拠**。round2のF-655-16〜21、round3/7のScope/AC改訂、F-655-15とP11引渡しが記録にある。ただし個々のfinding原本・当時のIssue/VDの完全snapshot・最終recheckは**原本未取得**。 |
| Issue #723／PR #731「実害判定基準を単一の正本に集約する」 | [マージ済みPR #731](https://github.com/hiratashinnya/review-system/pull/731)本文に「AC・検証設計と変更設計を独立レビューし、指摘是正後に合格」と明記 | **#655とは別の実1a/1b実施証言**。本文のfinding4件は後段の独立レビューであり、PlanReviewの4件と誤読しない。phase別finding、round、recheckの原本は未発掘。 |
| Issue #683／PR #809「karte handoff 検証（設計のみ先行）」 | [マージ済みPR #809のカルテ全文・finding](https://github.com/hiratashinnya/review-system/pull/809#issuecomment-6888926449)、[AttemptsとResults](https://github.com/hiratashinnya/review-system/pull/809#issuecomment-6888926694) | **実カルテ原本（コメント転載）**でround1〜7の状態遷移を追える。設計レビューround1〜4のF-809-01〜12は全12件`harm: real`でround4までにresolved。正式な1a/1b`plan-reviewer`とは記録されておらず、その件数に算入しない。 |
| PR #847「Codex委譲の既定化と上限時切替」 | [初回finding](https://github.com/hiratashinnya/review-system/pull/847#issuecomment-6896886321)、[オーナー決定](https://github.com/hiratashinnya/review-system/pull/847#issuecomment-6920614473)、[追加レビュー](https://github.com/hiratashinnya/review-system/pull/847#issuecomment-6934793848)、[実測と修正](https://github.com/hiratashinnya/review-system/pull/847#issuecomment-6938700848) | PRレビューの正負例・round継続であり1a/1bではない。new-12を「過去記録につき修正不要」と決定、new-16は実コードと規範の不整合、new-22はprobe実測の新たな欠陥。 |
| PR #846「review round 0件記録の基盤」 | [F-801-04 recheck](https://github.com/hiratashinnya/review-system/pull/846#issuecomment-6894808995) | 旧findingの証拠を照合してresolvedとした実例。後続HEADの全レビューが済んだという意味ではない。 |
| Issue #662／Issue #685・PR #695「非初回dispatchのdetached化」 | [Issue #662](https://github.com/hiratashinnya/review-system/issues/662)・[マージ済みPR #695](https://github.com/hiratashinnya/review-system/pull/695) | 1a同一branchの是正経路欠落と、1b dispatch/adoptの条件矛盾。**実行基盤障害2分類**であり、レビュー観点が悪いと数えない。 |

### finding → 根拠 → 承認済み条件 → 是正 → 再レビュー（公開原本で追跡可能な範囲）

| ID / 工程 | 原本・実害の根拠 | 承認済み条件／オーナー判断 | 是正 | 再レビュー・判定 |
| --- | --- | --- | --- | --- |
| **F-809-01／設計round1→2** | [原本](https://github.com/hiratashinnya/review-system/pull/809#issuecomment-6888926449)。verified申し送りと現在の`deferred_to`が一致しなければ無進捗除外が誤る（real/major）。 | #683のQ1=C・Q2=A・Q3=A、除外は無進捗に限定しverdictは不変。 | 設計書§4/§6/§7で行き先束縛と再チェック、実コード`ingest_apply`との整合を明示。 | 同じfinding IDの`rounds: [1, 2]`、`resolved_round: 2`。別URL正規化問題はF-809-08として区別。 |
| **F-809-07／設計round2→3** | [原本](https://github.com/hiratashinnya/review-system/pull/809#issuecomment-6888926449)。外部`gh`の失敗がCLIの終了コード契約から漏れる（real/major）。 | 既存CLIの失敗コード4、`verb_boundary._REFUSALS`を基準として確認。 | `FindingHandoffError(KarteUsageError)`で失敗種別を包み既存境界を保つ設計へ。 | `rounds: [2, 3]`、`resolved_round: 3`。新根拠の発見を重複扱いしない正例。 |
| **F-809-21／実装レビューround6→7** | [原本](https://github.com/hiratashinnya/review-system/pull/809#issuecomment-6888926449)。Codex側MCP経由の検査の限界（`harm: real`、`scope: out`）。 | オーナーは現構成の検査と限界の記録を選び、追加gateや回帰試験は採用しない。 | 設計書とREADMEに現在の実態・将来設定変更時の限界を明記。 | `rounds: [6, 7]`、`resolved_round: 7`。scope外でも実害を記録し、オーナー判断を無断変更しない例。 |
| **F-655-16〜21／実1a round2** | [Issue #662](https://github.com/hiratashinnya/review-system/issues/662)には「round2指摘をr3 branchで是正」の記述。個別finding本文は原本未取得。 | [PR #684](https://github.com/hiratashinnya/review-system/pull/684)はST/IT TCの実コード化を2a/test-writerとする決定、#663へ契約穴を分離。個別findingとの対応は**判定不能**。 | VD r2→r3の変更と新branchは確認可能。新branch自体は#662の別障害。 | 各IDのrecheck・旧基準・必要性は**判定不能**。未証明の是正成功や不合理な指摘とは記録しない。 |
| **F-655-15／実1a、詳細不明** | [PR #708](https://github.com/hiratashinnya/review-system/pull/708)がr22是正向けのF-655-15とP11に言及。finding原本は未取得。 | ownerがP11=B（CI専用step）を選択。`feedback-ledger`の当該entryは`source.round=0/finding_ids=[]`で、実レビューIDと直接束縛されていない。 | 1aのVDには判定条件を置き、実行方式の決定は1b CPへ入力する旨を台帳に記録。 | 元findingのrecheckは未取得。レビューが1aで方式まで強制すべきだったとは言えない。 |
| **new-12／PR #847** | [レビューと決定](https://github.com/hiratashinnya/review-system/pull/847#issuecomment-6920614473)。古い`#606/#628`文言。 | オーナーが「過去検証記録として残し、直さない」と決定。 | 編集なし。 | 新事実なしに要求を再掲しない**負例**。formal PlanReviewではない。 |
| **new-16／PR #847** | [原本](https://github.com/hiratashinnya/review-system/pull/847#issuecomment-6934793848)。継続検査`PREDECESSORS`が同一role再dispatchを拒否する。 | 既存の引渡し契約と実コードが基準。オーナーが是正Bを選択。 | [是正r4〜r7](https://github.com/hiratashinnya/review-system/pull/847#issuecomment-6938700848)にコード・Red→Green記録。 | 新規実害・根拠あるfindingの正例。実dispatchは当初未実測と限定。 |
| **F-801-04／PR #846** | [再レビュー原本](https://github.com/hiratashinnya/review-system/pull/846#issuecomment-6894808995)が保存先とSHA-256を確認。 | 旧レビューで要求した原本保存・再取込不一致拒否。 | 同じKarte保持領域で原本を保存し、digest・再取込拒否を加えた。 | 旧IDをresolvedと判定。後続変更に対する全体cleanは未証明。 |

### 実測できる分類と、測れない効果

1. **設計段階で正当な実害経路を指摘した例**：#809設計round1〜4のF-809-01〜12はカルテ上12件`harm: real`、同じ12件がround4までに`resolved`。当時の設計と既存コードの差分・検証計画を根拠にした早期検出の実例であり、製品障害の実発生率や1a/1bの検出率を示すものではない。
2. **不要な手戻りとして識別した要因**：#662（同一branch是正不可）、#685（dispatch/adoptの不整合）の実行基盤障害2分類。#655のreview後Scope/AC拡張は3種類の記録があるが、不当な要求増殖だった件数は**0件と確定したのではなく未測定**。#847の既決を再要求しない例は規範テスト材料であり、1aの誤指摘実測には算入しない。
3. **改善対象**：1aでは達成条件と方式決定の区別、1bでは前工程の既決照合、再レビューでは旧ID・旧snapshot・是正・新証拠の区別、scope外でも実害の記録、未決オーナー判断のSTOP。いずれも第一弾`plan-reviewer`規範へ対応済み。
4. **未測定**：正式PlanReviewの誤指摘率、1a/1bの平均ラウンド増分、#655の個別findingの妥当性・全再検証、#723の各round原本。**これらの未測定を「問題なし」や「完了」へ読み替えない**。

### 回帰テスト・合格基準との対応

- `tests/unit/test_plan_review_scope_856.py`：第一弾の規範条項検査。
- `tests/unit/test_plan_review_real_evidence_856.py` ＋ [cases.json](cases.json)：10の出典付き**実観測**を使った工程境界・オーナー決定・指摘ID維持/再レビューround・実害抑制禁止の契約ガード。各事例の対応条項を除く変異は失敗させる。レビューアの推論の正しさを実行測定するLLM E2Eではない。
- `tests/unit/test_plan_review_decision_examples_856.py`：`plan-reviewer.md`の実例に基づく**入力状況→期待するreviewer行動8件**を独立期待値で再生し、行動が逆転する編集と、元の句を残して「適用しない」を追記する意味反転の負例をRedにする。**これは契約の行動仕様を検証するオフライン試験であり、実LLMを起動した観測ではない**。
- #856 AC1の「複数の実1a/1b finding→根拠→承認→是正→再レビューの完全な対応」は#655・#723のraw PlanReview不足によりまだ達成宣言しない。**証拠不足を明示して対応表自体は作成済み**。
- AC2は正当な設計実害と実行基盤の手戻りを実測に基づいて切り分けた。ただしレビュー観点による不要な指摘数の評価は未測定で、これを0件と結論しない。
- AC4/5は規範への実例束縛と条項を機械確認できるようにしたが、独立した実LLMの1a/1b試験は別途必要で、**自動レビュアーの実測合格を主張しない**。
