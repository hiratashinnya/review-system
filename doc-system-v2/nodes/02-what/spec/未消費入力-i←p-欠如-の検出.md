**前提条件**: in-graph に分析層ノード（I）が存在する
**入力/トリガ**: P-3-1 がグラフ網羅性を確認する際に、I に P からの被依存辺（I←P）がないノードを検出する
**期待動作**: I←P 欠如のノードを検出したとき、未消費入力として RULE-006 の config `activate_stage: analysis` 行の severity で報告する
