**前提条件**: `always_error` に RULE-005 が登録されている（発火ステージ・suppress の状態に関わらず常に発火）
**入力/トリガ**: 完全孤立ノード（辺を1本も持たないノード）が存在する
**期待動作**: 完全孤立ノードが存在するとき、RULE-005 ERROR を報告する（always_error のため発火ステージ未達・suppress 指定でも抑制されない）
**例**: current_stage=requirements・`suppress: [RULE-005]` 指定でも、孤立ノードは `ERROR|...|RULE-005|...` として報告される
