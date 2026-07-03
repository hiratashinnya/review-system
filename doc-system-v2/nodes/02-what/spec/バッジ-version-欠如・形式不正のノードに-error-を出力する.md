**前提条件**: in-graph にノードが1件以上存在し、各ノードの summary バッジが走査済みである。
**入力/トリガ**: 検証ツールが `· v` 部分の欠如、または `X.Y.Z` が非負整数 3 部形式でないバッジを1件以上検出する。
**期待動作**: バッジ version 欠如または形式不正を検出したとき、当該ノードを指す ERROR を1件出力する。
**違反例**: `⬡ SPEC-99`（`· vX.Y.Z` 部分なし）→ `ERROR|{file}:{line}|NFR-4-check|SPEC-99|node badge version missing` を出力。`⬡ SPEC-88 · v0.2`（Z 部分欠如）→ `ERROR|{file}:{line}|NFR-4-check|SPEC-88|node badge version format error: v0.2` を出力。
