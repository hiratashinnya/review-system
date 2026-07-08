**もの**: config.yaml の always_error セクション（scheduled/activate_stage の発火制御に関わらず常時 ERROR として発火させる RULE 番号リスト）
**種別**: 内部データ（系外へ出ない）
**生成元**: P-5-3（設定スライス組立）に依存（D→P）
**消費先**: P-2-5（発火・重症度確定プロセス）のみが P→D-12 で消費
**含むフィールド**: `always_error`（常時 ERROR 発火 RULE 番号のリスト。例 [RULE-005, RULE-007]）

**スタンプ結合解消**: 発火・重症度確定を担う P-2-5 だけが受ける最小スライス。各検査子が always_error を直接参照しない。
