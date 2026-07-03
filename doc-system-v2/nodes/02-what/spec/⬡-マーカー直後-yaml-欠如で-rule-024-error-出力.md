**前提条件**: in-graph ファイルに `⬡` マーカー行が1件以上存在する。
**入力/トリガ**: `⬡` マーカー行の直後行が ```` ```yaml ```` ブロック開始行でない（heading／空行＋heading／別の `⬡` マーカーが直後に来る）。
**期待動作**: `⬡` マーカー直後に YAML ブロックがないとき、`ERROR|{file}:{line}|RULE-024|(none)|⬡ marker at line N has no YAML block following` を出力する。
