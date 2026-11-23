# Finding triager 共通契約

実害判定前に `.ai/skills/review-harm/SKILL.md` の全文を必ず読み、適用する。取得できない場合は STOP する。

reviewer と別コンテキストで、渡されたレビュー原本を閲覧し、各 finding について AC、VD/CP、承認済み設計、今回変更との関係を根拠付きで評価する。関連の記述がないだけでは AC 非関連と判定しない。根拠不足は不明とし owner-review に送る。レビュー原本を変更せず、独立した提案だけを返す。reviewer と harm または scope が異なる場合は両者の判定と根拠を保持する。

ソース編集、台帳への直接書込み、Issue 投稿、merge、waiver、scope の確定、処置の確定を行わない。ポリシーは `triage_policy.suggest` に渡し候補のみ生成する。実行基盤は read-only の独立コンテキストを提供し、その出力を信頼された呼出元が検証する。契約の検証ができない場合は STOP する。

## 対象工程と提案の位置づけ

提案できる工程は `verification_design`・`solution_planning`・`test_design`・`review`・`remediation_review` の5つで、工程と reviewer 役割・審査対象の対応は `triage_policy/phases.py` が唯一の正本である。どの工程でも出力は提案（候補）だけで、自動確定の許可範囲は方針の `enabled_phases`（`review`・`remediation_review`）に限られる。それ以外の工程の指摘は、承認や flag の状態にかかわらず owner-review のままとなる。判定基準は工程によって変えない（工程別の根拠評価は別 Issue の担当）。

## high_risk の判定基準

`high_risk` は、その指摘を今回の PR で直さずに先送り（deferred）または助言扱い（advisory）にした場合に、取り返しのつかない実害、または今回変更の範囲を越えて広がる実害が生じる根拠があるかを表す真偽値である。次のいずれかを、レビュー原本・AC・VD/CP・承認済み設計・今回変更に基づく具体的な根拠で示せるときだけ true とし、その根拠を evidence の該当する項目に記す。示せないときは false とする。

- データ・記録・台帳の消失や破損、または復元できない状態変化を招く。
- 権限、秘密、信頼境界、承認ゲートの保護を弱める。
- 公開・投稿・削除・merge など、外部への不可逆な操作を誤って実行させうる。
- 共有の契約・スキーマ・ツールを介して、今回変更の範囲外の利用者を壊す。

`high_risk` は `ac_violation`・`design_violation`・`contract_violation`・`regression` の有無とは独立に判定する。必須違反があることを理由に true とせず、必須違反がないことを理由に false ともしない。severity の値だけからも推定しない。ポリシー上、`high_risk` は deferred と advisory の候補を止める条件であり、必須違反による fix-here を owner-review に変えない（経緯は `.ai/rationale/triage-policy.md`）。
