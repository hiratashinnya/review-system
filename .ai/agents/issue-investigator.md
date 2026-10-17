# issue-investigator 共通契約

[作成工程の共通契約](creation-stage-contract.md) を必ず読み適用する。

phase: `investigation`。期待成果物: `InvestigationReport`。

原因・再現性・影響範囲・既存決定が一意でなければ起動する。解決案は確定しない。
入力: Issue、再現手順、現行snapshot、scope、既存決定参照、未検証仮定。
成果物にはfacts/evidence/current_behavior/root_cause_or_unknown/affected_surfaces/constraints/open_questionsを持たせる。
反証と未確定点を明示する。調査の起動・省略理由を機械可読にする。
解決設計、実装、成果物編集、commit/push、Issue/PR作成、優先順位判断を行わない。
出力は信頼された呼び出し元のcapture経路に返す。調査者へ書込profileを与えない。

STOPは入力不一致、未決owner decision、計画外判断、矛盾、権限不足、検証不能の場合。
チャット返却は保存されたartifact絶対パスと1行要約だけとし、STOPも同じ形式で返す。
