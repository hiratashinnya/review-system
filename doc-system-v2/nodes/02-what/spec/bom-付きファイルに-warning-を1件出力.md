**前提条件**: `trace_scope.include` に一致する in-graph ファイルのうち1件が、先頭に BOM（`\xEF\xBB\xBF`）を持つ。
**入力/トリガ**: 検証ツールが当該ファイルを読み込み、先頭 BOM を検出する。
**期待動作**: 先頭 BOM を検出したとき、当該ファイルに対し WARNING を1件出力する。
**例**: `doc-system/02-what/01-fr.md` の先頭に BOM が存在 → 当該ファイルに WARNING を1件出力する。
