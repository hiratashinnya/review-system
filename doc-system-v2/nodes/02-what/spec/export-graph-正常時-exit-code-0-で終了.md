**前提条件**: spec-inspector がノードグラフを正常にパース済みで、グラフに1件以上のノードが存在し、`--export-graph` に有効なフォーマット名と出力先ファイルパスが指定され、グラフファイルが正常に書き出される。
**入力/トリガ**: `spec-inspector --export-graph dot ./output/graph.dot` を実行する。
**期待動作**: グラフファイル出力が正常完了したとき、exit code 0 で終了する。
**合格例**: `--export-graph dot ./graph.dot` 実行でファイルが正常生成され、プロセスが exit code 0 で終了する。
**違反例**: ファイルは生成されたが exit code が 0 以外で終了する → 期待動作を満たさない。
