**前提条件**: suppress 機構が動作しており、存在しない ID 参照を含むノードがある
**入力/トリガ**: ノードの `suppress` リストに RULE-007 が含まれる
**期待動作**: suppress に RULE-007 が含まれるとき、RULE-007 の ERROR を報告する（always_error のため抑制不可）。
