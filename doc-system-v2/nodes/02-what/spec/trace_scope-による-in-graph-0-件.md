**概要**: trace_scope の結果 in-graph が0件のときの振る舞い。検証アサーションは子 SPEC-31-1〜4 を参照（違反0件報告・ノード0件報告・終了コード・ルールスキップを1アサーション1SPEC に分割・FND-58）。
**親辺根拠**: in-graph 0件はノードファイルのパース可否ではなく、`trace_scope.include`/`exclude` によるトレース対象集合の決定結果であるため、親は FR-9（トレース対象集合の宣言）とする。
**例**: `trace_scope.include: ["doc-system/**/*.md"]` かつ `exclude: ["doc-system/**/*.md"]` → in-graph ファイル0件・ノード0件・違反0件・終了コード 0。
