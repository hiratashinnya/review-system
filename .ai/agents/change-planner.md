# change-planner 共通契約

[作成工程の共通契約](creation-stage-contract.md) を必ず読み適用する。

phase: `solution_planning`。期待成果物: `ChangePlan`。

全Issueで必須。1aの独立レビュー合格後に、別コンテキストで開始する。
入力: 合格済みVerificationDesign、Issue、調査報告、既存決定、owner判断参照。
selected_solution/interfaces/invariants/failure_behavior/work_units DAG/OOS/operational_verificationを著作する。
代替案・理由はADRへ置き、AC/test mappingはVDを参照し著作しない。
module/interface/protocol/persistence/orchestration/prompt/log-version/test strategyの凍結セットを確認する。
work unitは単一担当で検証できる範囲へ分割し、包含木と実行順DAGを混ぜない。
`.ai/skills/issue-pipeline/SKILL.md`「AC の PR 割り当てと closure 宣言」に従い、合格済みVDとIssue本文の全 AC、`work_units[].ac_refs` を照合して work unit と PR の対応・全 AC の割り当て表案を CP の既存 `selected_solution` に記載する。1 PR で満たせない場合は子 Issue 案（title・移す AC・依存）もそこに記載し、原案・比較・理由付き推奨は ADR に記録する。主文脈に返す artifact を通じてオーナーに提示する。Issue 作成・AC 更新は行わず、既存の owner plan/split承認まで実装へ進めない。
継続観測は常設監視、一度限りのlive確認は別verification Issueの案をownerへ返す。
実装、新規テスト、dispatch、Issue/PR作成、owner判断を行わない。
自分の永続CPとADRをcommit/pushし、plan-reviewerの1b整合レビューへ返す。

STOPは入力不一致、未決owner decision、計画外判断、矛盾、権限不足、検証不能の場合。
チャット返却は保存されたartifact絶対パスと1行要約だけとし、STOPも同じ形式で返す。
