**前提条件**: in-graph ファイルに `⬡` マーカーと YAML ブロックが存在し、YAML パース可能で `id` キーは存在する。
**入力/トリガ**: YAML ブロックに `type` キーが存在しない、または値が空文字列である。
**期待動作**: `type` キーが欠如・空のとき、`ERROR|{file}:{line}|RULE-026|{id}|type field missing or empty` を出力する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に type なし・id は `FR-1` → `ERROR|doc-system/02-what/01-fr.md:17|RULE-026|FR-1|type field missing or empty`。
