**前提条件**: `config.yml` が PROMPT ノードカバレッジ対象 skill 集合を宣言済み（姉妹 SPEC「config.yml が PROMPT ノードカバレッジ対象 skill 集合を宣言する」充足）で、doc-system の PROMPT 型ノード群が読み込み済みである。
**入力/トリガ**: 検査系（validate.py／spec-inspector）が `config.yml` の宣言済み対象 skill 集合の各 skill について、対応する在グラフ PROMPT ノードの有無を走査する。
**期待動作**: 宣言された対象 skill 集合のうち、対応する PROMPT ノードが在グラフに**存在しない skill**（未モデル化 skill）があれば、その欠落を機械判定して報告する（存在方向を検査するカバレッジ／網羅性 RULE）。
**例**: 対象 skill `test-strategy` に対応する PROMPT ノードが在グラフに不在 → 当該 skill の欠落を報告。宣言 14 件（docidx を含む）すべてに対応 PROMPT が存在すれば 0 件で通過。

- **provenance / 位置づけ**: 傘 SPEC-61（`対象 skill の LLM プロンプト資産を設計層 PROMPT ノードで在グラフモデル化`）の子。issue #63 の前提として新設する RULE-032 の挙動を規定する。実装位置＝`config.yml` の `rule_activation` に RULE-032 を登録し、判定ロジックは `dsv2/query.py` の `prompt_coverage_gaps()`（宣言 skill 集合のうち対応 PROMPT ノード不在の skill を列挙）に実装、`dsv2/cli.py` の `prompt-coverage` サブコマンドで公開する。決定元＝DD-22（2026-07-01 オーナー確定）。
- **姉妹 SPEC-61-1（存在アサーション）を enforceable にする**: 姉妹 SPEC「対象 skill 集合の各 skill に対応する PROMPT ノードが在グラフに存在する」は存在を要求するが、既存 `must_link_to: {node: PROMPT, target: SPEC}` は**在グラフ PROMPT ノードが親辺を持つか（逆方向）**しか検査せず、宣言集合に対する PROMPT ノードの**欠落方向（未モデル化 skill の検出）**は機械強制されていなかった。本 SPEC はこの欠落方向のカバレッジ RULE を規定し、SPEC-61-1 を実際にテスタブル／強制可能にする（config 宣言集合 → 欠落 PROMPT を flag）。
- **接続規則との関係**: 本 SPEC が規定する RULE は既存 PROMPT→SPEC 親辺検査（逆方向）とは別軸の網羅性検査であり、config に新 RULE を追加する（RULE 新設は本 SPEC 駆動＝FND-102／FND-103 の SPEC 駆動慣行に倣う）。
- **指摘時 ref_version（DD-3・辺を張る対象分）**: 傘 SPEC-61 "0.1"（親 SPEC→SPEC 辺・`対象-skill-の-llm-プロンプト資産を設計層-prompt-ノードで在グラフモデル化` 現バッジ v0.1.0 時点＝x.y "0.1"）。
