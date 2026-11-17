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
