**前提条件**: in-graph ファイルに `⬡` マーカー行が存在し、その直後の YAML ブロック自体は存在する（マーカー欠落ではなく中身の構文不正のケース）。
**入力/トリガ**: その YAML ブロックが PyYAML safe_load で ScannerError または ParserError を発生させる（インデント不正・コロン欠如等）。
**期待動作**: YAML パースが例外を発生させたとき、`ERROR|{file}:{line}|RULE-023|(none)|YAML parse error: {例外メッセージ}` を 1 件出力する。
**例**: `doc-system/02-what/01-fr.md` 行17の YAML に不正インデント → `ERROR|doc-system/02-what/01-fr.md:17|RULE-023|(none)|YAML parse error: mapping values are not allowed here` を出力する。
