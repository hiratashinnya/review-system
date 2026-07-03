**もの**: `config.yaml` の各セクション（フェーズ/ステージ・接続規則・抑制対象外・トレース対象等）を検査ロジックが参照しやすい形に分解した設定値オブジェクト群の総称。
**用途**: config（MOD-2）が `config.yaml` を読込・スキーマ検証して組み立て、各 checker / collector / projector が検査条件（必須辺・activate_stage・severity・always_error・trace_scope 等）を引くために参照する。
**Python 型名**: `ConfigSlice`（D-9〜D-16 各スライスに対応する値オブジェクト群）
**保持要素**: フェーズ/ステージ定義・must_link_to / must_be_linked_from・decision_spine・rule_activation・condition_vocab・coverage_rules・always_error・trace_scope 等のスライス
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）
