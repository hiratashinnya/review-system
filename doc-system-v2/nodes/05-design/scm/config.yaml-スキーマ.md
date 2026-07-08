ドキュメントシステムのグローバル設定ファイル `config.yaml`（I-5）が満たすべきトップレベル構造の傘スキーマ。検証ツール（P-5 設定読込・検証）がルール発火・必須接続・always_error fail-close を判定するために読む全セクションの構造を定義する。具体スキーマは配下の子に分割する：SCM-2-1（接続ルール＝must_link_to／must_be_linked_from）／SCM-2-2（ライフサイクル・決定スパイン＝fnd_lifecycle／decision_spine）／SCM-2-3（ステージ・語彙・カバレッジ・スコープ＝current_phase/current_stage/phases/stages/rule_activation/condition_vocab/coverage_rules/always_error/trace_scope）。階層は -N 採番で表現し親→子辺は持たない。

**フォーマット**: YAML（単一ファイル `docs/doc-system/config.yaml`）
**必須フィールド（トップレベルセクション）**: current_phase・current_stage・phases・stages・must_link_to・must_be_linked_from・fnd_lifecycle・decision_spine・rule_activation・condition_vocab・coverage_rules・always_error・trace_scope（詳細は SCM-2-1〜2-3 が規定）
