**Python クラス**: `ConfigSlice`（`PhaseStateSlice` / `LinkRuleSlice` / `DecisionSpineSlice` / `AlwaysErrorSlice` / `ConditionSlice` / `RuleActivationSlice` / `ScopeSlice` 等の不変値オブジェクト群を束ねる集約）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: config.yaml の各セクションを型付き値オブジェクトとして表す不変スライス群。config（MOD-2）が組み立て、各検査モジュールが必要なスライスを消費する。
**フィールド**（スライスと対応 D）:
- `PhaseStateSlice` — current_phase / current_stage / phases / stages（D-9 フェーズ・ステージ状態）
- `LinkRuleSlice` — must_link_to / must_be_linked_from（D-10 必須接続規則）
- `DecisionSpineSlice` — decision_spine（D-11 決定スパイン規則）
- `AlwaysErrorSlice` — always_error（D-12 always-error 規則）
- `ConditionSlice` — condition_vocab / coverage_rules（D-13 condition 語彙・網羅規則）
- `RuleActivationSlice` — rule_activation（D-14 ルール発火ステージ表）
- `HubThresholdSlice` — ハブ閾値（D-15 ハブ閾値設定・post-mvp）
- `ScopeSlice` — trace_scope（D-16 走査スコープ設定）
**不変条件**: 各スライスは frozen で生成後に変更不可。参照先 D の必須フィールドを欠かさず保持する。
**実現する D**: D-9（フェーズ・ステージ状態）/ D-10（必須接続規則）/ D-11（決定スパイン規則）/ D-12（always-error 規則）/ D-13（condition 語彙・網羅規則）/ D-14（ルール発火ステージ表）/ D-15（ハブ閾値設定）/ D-16（走査スコープ設定）
