**前提条件**: 対象 skill に対応する PROMPT ノードが在グラフに存在する（SPEC-61-1 充足済み）。
**入力/トリガ**: spec-inspector が各 skill PROMPT ノードのキャリア属性を参照する。
**期待動作**: 各 skill PROMPT ノードが届け方を表すキャリア属性を1つ持ち、その値が `skill` または `agent` のいずれかであることを判定する。
**例**: skill `align` の PROMPT ノードが `carrier: skill` を持つ → 属性充足。将来 orchestrator agent 化時は `carrier: agent`＋版更新で表し、別 SPEC 軸へ付け替えない。
