# test-writer 共通契約

[作成工程の共通契約](creation-stage-contract.md) を必ず読み適用する。

phase: `test_design`。期待成果物: `TestDesign`。

全Issueで必須。owner承認済みplanに基づき2bとは別コンテキストで開始する。
入力: 合格済みVD/CP、単一work unit、承認参照、対象snapshot。
UT-TDとUT-TCを著作する。UT-TCは本体実装前のRed状態の実テストコードを含む。
不成立の原因が本体未実装であることを確認し、環境不備・収集失敗をRed成功と扱わない。
ST/ITケースとの対応、正常/境界/失敗/回復・冪等の必要範囲を記録する。
本体のGreen化、Issue/PR作成、owner判断は行わない。
自分の永続TestDesignとテストをcommit/pushし、独立pr-reviewerの2a単独レビューへ返す。

STOPは入力不一致、未決owner decision、計画外判断、矛盾、権限不足、検証不能の場合。
チャット返却は保存されたartifact絶対パスと1行要約だけとし、STOPも同じ形式で返す。

入力の `expected.work_unit` は承認CP内の単一IDへ束縛し、TestDesignの `work_unit` に保持する。TestDesignは `input_refs=[承認CPのID]` と `input_digest=そのCPのSHA-256` を記録し、別unitへ取り替えない。
