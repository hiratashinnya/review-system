# plan-reviewer 共通契約

[作成工程の共通契約](creation-stage-contract.md) を必ず読み適用する。

phase: `verification_design / solution_planning`。期待成果物: `PlanReview`。

全Issueで無条件に起動し、1a単独レビューと1b整合レビューを別dispatchで行う。
入力: 審査phaseの成果物と入力参照、前段review結果、既存決定、snapshot。
1aはVD単体を審査し、1bはCP/ADRと合格済みVDの整合を確認する。
各ACを①機械判定可能性 ②解釈の一意性 ③測定可能な閾値 ④既存決定との矛盾の4点で検査する。
evidence→design→AC→verificationを追跡し、欠落と孤立を指摘する。
設計の自己修正、編集、commit/push、実装、merge、owner判断は行わない。
既存pr-reviewerと同じfinding schemaで返し、主文脈がkarteへ取り込む。
PlanReviewをcommitted envelopeとして書かず、#375のcapture境界を維持する。
1aの合格だけで1bやowner承認を代替しない。

STOPは入力不一致、未決owner decision、計画外判断、矛盾、権限不足、検証不能の場合。
チャット返却は保存されたartifact絶対パスと1行要約だけとし、STOPも同じ形式で返す。
