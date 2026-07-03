**前提条件**: `trace_scope.include` に一致する in-graph ファイルが1件以上存在し、いずれも BOM なしの正常な UTF-8 でエンコードされている。
**入力/トリガ**: 検証ツールが in-graph ファイルを `file.read_text(encoding='utf-8', errors='strict')` で読み込む。
**期待動作**: 正常 UTF-8 ファイルを読み込んだとき、全 in-graph ファイルの読み込みがエラーなく完了する（違反 0 件）。
**例**: `doc-system/02-what/01-fr.md` を `open(..., encoding='utf-8', errors='strict').read()` → 読み込み成功 → 違反 0 件。
