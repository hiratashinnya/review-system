ドキュメントシステム検証ツールが読み込むグローバル設定の単一インスタンス。SCM-2 スキーマに準拠し、ルール発火・抑制・ステージ判定・接続検査・ライフサイクルの全パラメータをここに集約する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: トップレベル13要素を配下の子 CFG に分解。`current_phase`（CFG-1-1）・`current_stage`（CFG-1-2）・`phases`（CFG-1-3）・`stages`（CFG-1-4）・`must_link_to`（CFG-1-5）・`must_be_linked_from`（CFG-1-6）・`fnd_lifecycle`（CFG-1-7）・`decision_spine`（CFG-1-8）・`rule_activation`（CFG-1-9）・`condition_vocab`（CFG-1-10）・`coverage_rules`（CFG-1-11）・`always_error`（CFG-1-12）・`trace_scope`（CFG-1-13）。
