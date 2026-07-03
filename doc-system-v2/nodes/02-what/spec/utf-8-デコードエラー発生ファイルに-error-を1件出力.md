**前提条件**: `trace_scope.include` に一致する in-graph ファイルのうち1件が、UTF-8 として不正なバイト列を含む。
**入力/トリガ**: 検証ツールが当該ファイルを `errors='strict'` で読み込み、UTF-8 デコードエラーに遭遇する。
**期待動作**: UTF-8 デコードエラーが発生したとき、当該ファイルに対し ERROR を1件出力する。
**例**: バイナリデータを含む `doc-system/corrupt.md` が in-graph に存在 → `ERROR|doc-system/corrupt.md:0|NFR-1-check|(none)|UTF-8 decode error` を出力する。
