**Python クラス**: `InspectionViews`（`LinkageView` / `AttributeView` / `DecisionEdgeView` / `AnalysisTopologyView` / `SpecCoverageView` の不変値オブジェクト群を束ねる集約・`@dataclass(frozen=True)`）
**パス**: `spec_inspector/domain.py`（MOD-1）
**責務**: D-4（構造化ノードセット）から射影した各検査ビュースライスを型付き値オブジェクトとして表す不変集約。projector（MOD-13）が `project_views(node_set) -> InspectionViews` で組み立て、各検査モジュールが必要なビューを消費する。DM-4（ConfigSlice 型群）の射影側対応物。
**フィールド**（スライスと対応 D）:
- `LinkageView` — id・type・edges(to)・in_degree・out_degree・全ノード ID 集合・階層 ID パターン（D-17 接続検査ビュー。消費: structure_checker MOD-14）
- `AttributeView` — id・type・condition・result・log_ref・suppress・scheduled・辺メタデータ（D-18 属性検査ビュー。消費: condition_checker MOD-15・verification_checker MOD-16・filter MOD-6）
- `DecisionEdgeView` — 辺の from_id・to・ref_version・参照先バッジ x.y・DD/Q/PEND 義務辺情報（D-19 決定辺ビュー。消費: drift_checker MOD-5）
- `AnalysisTopologyView` — 分析層ノード（type ∈ {I,O,D,P,E}）の id・type・edges(to)（D-20 分析層トポロジビュー。消費: graph_coverage MOD-7）
- `SpecCoverageView` — FR/SPEC/TD の id・condition・edges(to)（D-21 仕様カバレッジビュー。消費: spec_coverage MOD-17）
**不変条件**: 各ビューは frozen で生成後に変更不可。`LinkageView.in_degree` / `out_degree` は非負整数で全ノード ID 集合と整合。各ビューは参照先 D の必須フィールドを欠かさず保持する。D-22（グラフトポロジビュー・post-mvp）は本集約に含めない（labels:[post-mvp]・対象外）。
**実現する D**: D-17（接続検査ビュー）/ D-18（属性検査ビュー）/ D-19（決定辺ビュー）/ D-20（分析層トポロジビュー）/ D-21（仕様カバレッジビュー）

> **新設理由（FND-100・PR #32 レビュー対応）**: D-17〜D-21（各検査ビュー型）を 1 ノードで一括 realize。先例 DM-4（ConfigSlice 型群・D-9〜D-16 を 1 ノード集約）と射影系として構造一致。MOD-13 が `project_views(node_set) -> InspectionViews` で集約戻り値型を既に命名済み。これにより D-17〜D-21 経路の `DM→MOD→D` チェーン欠落を補完。`→FND-100` バックリファレンス付与。
