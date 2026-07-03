**パス**: `spec_inspector/projector.py`
**責務**: P-1-6（検査ビュー射影）を実現する。D-4（構造化ノードセット）を消費スライス D-17〜D-21 へ射影する。
**公開 I/F**: `project_views(node_set) -> InspectionViews`
**依存**: domain（NodeRecord / 各消費スライス値オブジェクト）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: P-1-6（検査ビュー射影）は孫プロセスを持たないが「ビュー工場」として責務が独立するため、parser.py（MOD-4）から分離して新設。
