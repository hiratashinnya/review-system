**前提条件**: in-graph に `type: DD`・`type: Q`・`type: PEND` のいずれかのノードが1件以上存在し、ライフサイクル状態は本文見出しバッジ（`**status: open**` 等）にのみ記載されている。
**入力/トリガ**: 検証ツールが、ノード YAML（メタ属性）に `status:`・`lifecycle:`・`state:` キーを持たない DD・Q・PEND ノードを検査する。
**期待動作**: status 系キーがノード YAML（メタ属性）に存在しないとき、当該ノードを違反なしとして通過させる。
**例**: `{id: "DD-5", type: "DD", labels: [], scheduled: "", edges: []}` → status 系フィールドなし → 違反なし。
