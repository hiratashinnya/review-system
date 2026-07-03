**前提条件**: spec-inspector がノードグラフを正常にパース済みで（SPEC-1 の正常系が先行）、グラフに1件以上のノードが存在し、`--export-graph` に有効なフォーマット名（`dot` または `json`）と出力先ファイルパスが指定されている。
**入力/トリガ**: `spec-inspector --export-graph dot ./output/graph.dot`（または `json` フォーマット・任意の出力先パス）を実行する。
**期待動作**: `--export-graph` を実行したとき、指定フォーマット（`dot`＝Graphviz dot 形式・`json`＝JSON 隣接リスト形式）で依存関係グラフを指定ファイルパスに書き出す。
**合格例**: ノード 3 件（SPEC-1→FR-1、FR-1→SR-1）に `--export-graph dot ./graph.dot` を実行 → `./graph.dot` に `digraph { "SPEC-1" -> "FR-1"; "FR-1" -> "SR-1"; }` 形式の dot ファイルが生成される。
**違反例**: 出力ファイルが生成されない・または dot 形式として不正なテキスト（例: JSON 形式）が書き出される → 期待動作を満たさない。
