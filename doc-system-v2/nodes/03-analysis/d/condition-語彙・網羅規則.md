**もの**: config.yaml の condition_vocab・coverage_rules の 2 フィールドを束にした condition 関連規則
**種別**: 内部データ（系外へ出ない）
**生成元**: P-5-3（設定スライス組立）に依存（D→P）
**消費先**: P-2-3-1〜4（カバレッジ属性検査リーフ）・P-3-2-1（FR×condition 充足集計）が P→D-13 で消費
**含むフィールド**: `condition_vocab`（有効な condition 値リスト）・`coverage_rules`（FR の required_conditions / recommended_conditions）

**スタンプ結合解消**: 構造検査・決定辺系プロセスが condition_vocab/coverage_rules を受けずに済む。
