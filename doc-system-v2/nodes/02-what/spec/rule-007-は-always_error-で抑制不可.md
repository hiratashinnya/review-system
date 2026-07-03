**前提条件**: 存在しない ID を指す辺があり RULE-007 が発火する状態である
**入力/トリガ**: 当該ノードに `suppress: [RULE-007]`（または `scheduled` / 未達 `activate_stage`）が設定されている
**期待動作**: 抑制指定が設定されているとき、RULE-007 を抑制せず ERROR を報告する（always_error）。
