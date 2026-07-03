**前提条件**: in-graph ファイルに `⬡` マーカーと直後の YAML ブロックが存在し、YAML は safe_load でパース可能である。
**入力/トリガ**: YAML ブロックに `id` キーが存在しない、または値が空文字列（`id: ""`）である。
**期待動作**: `id` キーが欠如・空のとき、`ERROR|{file}:{line}|RULE-025|(none)|id field missing or empty` を出力する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に id キーなし → `ERROR|doc-system/02-what/01-fr.md:17|RULE-025|(none)|id field missing or empty`。
