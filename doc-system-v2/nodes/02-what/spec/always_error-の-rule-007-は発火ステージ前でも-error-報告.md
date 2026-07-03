**前提条件**: `always_error` に RULE-007 が登録されている（発火ステージ・suppress の状態に関わらず常に発火）
**入力/トリガ**: 存在しない ID を参照する辺が存在する
**期待動作**: 存在しない ID 参照が存在するとき、RULE-007 ERROR を報告する（always_error のため発火ステージ未達・suppress 指定でも抑制されない）
**例**: current_stage=requirements・`suppress: [RULE-007]` 指定でも、dangling 辺は `ERROR|...|RULE-007|...` として報告される
