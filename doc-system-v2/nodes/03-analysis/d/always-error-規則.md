**もの**: config.yaml の always_error セクション（suppress/scheduled/activate_stage いずれでも抑制不可の RULE 番号リスト）
**種別**: 内部データ（系外へ出ない）
**生成元**: P-5-3（設定スライス組立）に依存（D→P）
**消費先**: P-2-5（抑制・発火フィルタ）のみが P→D-12 で消費
**含むフィールド**: `always_error`（抑制不可 RULE 番号のリスト。例 [RULE-005, RULE-007]）

**スタンプ結合解消**: 抑制フィルタ P-2-5 だけが受ける最小スライス。各検査子が always_error を直接参照しない。
