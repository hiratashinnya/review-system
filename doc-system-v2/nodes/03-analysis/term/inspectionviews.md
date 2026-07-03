**もの**: D-4（構造化ノードセット）を検査子向けに射影した検査ビュースライス値オブジェクト群の総称。接続検査・属性検査・決定辺・分析層トポロジ・仕様カバレッジの各ビューを束ねた集約で、各ビューは D-4 の部分射影に固有の計算フィールド（in_degree / out_degree 等）を加えたもの。
**用途**: projector（MOD-13）が D-4 を一括射影して組み立て、各 checker / coverage / projector 消費側（structure_checker・condition_checker・verification_checker・drift_checker・graph_coverage・spec_coverage）が必要なビューだけを受け取って検査入力とする。DM-4（ConfigSlice 型群）が config を分解した集約であるのに対し、InspectionViews は D-4 を分解した射影側の集約。
**Python 型名**: `InspectionViews`（D-17〜D-21 各ビューに対応する値オブジェクト群を束ねる集約）
**保持要素**: `LinkageView`（D-17 接続検査）・`AttributeView`（D-18 属性検査）・`DecisionEdgeView`（D-19 決定辺）・`AnalysisTopologyView`（D-20 分析層トポロジ）・`SpecCoverageView`（D-21 仕様カバレッジ）の各スライス
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）

> **TERM→SPEC 上流の根拠**: D-17（接続検査ビュー）の上流 SPEC-5 を集約代表として張る（DM-4↔TERM-4 が代表 SPEC を 1 本張る先例に倣う）。D-18〜D-21 の各上流（SPEC-15/9/29/14）はビュー単位 D ノード側で既に表現済み。
