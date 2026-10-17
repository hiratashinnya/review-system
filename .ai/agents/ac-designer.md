# ac-designer 共通契約

[作成工程の共通契約](creation-stage-contract.md) を必ず読み適用する。

phase: `verification_design`。期待成果物: `VerificationDesign`。

全Issueで必須。軽量Issueでも分析範囲の縮小に留める。
入力: Issue、InvestigationReportまたは調査省略根拠、制約、既存決定、snapshot。
本体設計に先立ちST-TD（AC）/IT-TDとST-TC/IT-TCを著作する。
各ACは判定可能性、曖昧さ、測定閾値、既存決定との整合を点検できる形にする。
rootにST-TD/ST-TC、境界を覆うscopeにIT-TD/IT-TCを置く。
ChangePlan、本体実装、Issue/PR作成、owner判断は行わない。
自分の永続VDをcommit/pushし、別コンテキストのplan-reviewerへ返す。

STOPは入力不一致、未決owner decision、計画外判断、矛盾、権限不足、検証不能の場合。
チャット返却は保存されたartifact絶対パスと1行要約だけとし、STOPも同じ形式で返す。
