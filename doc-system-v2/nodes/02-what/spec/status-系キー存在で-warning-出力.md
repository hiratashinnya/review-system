**前提条件**: in-graph に `type: DD`・`type: Q`・`type: PEND` のいずれかのノードが1件以上存在し、ライフサイクル状態は本文見出しバッジに記載されるべきものである。
**入力/トリガ**: 検証ツールが、ノード YAML（メタ属性）に `status:`・`lifecycle:`・`state:` のいずれかのキーを持つ DD・Q・PEND ノードを検査する。
**期待動作**: status 系キーがノード YAML（メタ属性）に存在するとき、WARNING を1件出力する。
**例**: `{id: "Q-3", type: "Q", labels: [], scheduled: "sprint-1", status: "open", edges: []}` → `WARNING|{file}:{line}|NFR-6-check|Q-3|lifecycle field 'status' in node YAML violates NFR-6` を出力。
