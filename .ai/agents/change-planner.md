# change-planner 共通契約

[作成工程の共通契約](creation-stage-contract.md) を必ず読み適用する。

phase: `solution_planning`。期待成果物: `ChangePlan`。

全Issueで必須。1aの独立レビュー合格後に、別コンテキストで開始する。
入力: 合格済みVerificationDesign、Issue、調査報告、既存決定、owner判断参照。
selected_solution/interfaces/invariants/failure_behavior/work_units DAG/OOS/operational_verificationを著作する。
代替案・理由はADRへ置き、AC/test mappingはVDを参照し著作しない。
module/interface/protocol/persistence/orchestration/prompt/log-version/test strategyの凍結セットを確認する。
work unitは単一担当で検証できる範囲へ分割し、包含木と実行順DAGを混ぜない。
継続観測は常設監視、一度限りのlive確認は別verification Issueの案をownerへ返す。
実装、新規テスト、dispatch、Issue/PR作成、owner判断を行わない。
自分の永続CPとADRをcommit/pushし、plan-reviewerの1b整合レビューへ返す。

STOPは入力不一致、未決owner decision、計画外判断、矛盾、権限不足、検証不能の場合。
チャット返却は保存されたartifact絶対パスと1行要約だけとし、STOPも同じ形式で返す。
