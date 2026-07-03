**前提条件**: in-graph に分析層ノード（O）が存在する
**入力/トリガ**: P-3-1 がグラフ網羅性を確認する際に、O に P への依存辺（O→P）がないノードを検出する
**期待動作**: O→P 欠如のノードを検出したとき、未駆動出力として RULE-006 の config `activate_stage: analysis` 行の severity で報告する
