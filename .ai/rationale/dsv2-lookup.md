# dsv2-lookup — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/dsv2-lookup.md`](../agents/dsv2-lookup.md) にある。

このエージェントの対象を doc-system v2 に限定したのは、v1 の `docidx` と v2 の slug/path/schema 契約を同じ検索手順で扱うと、旧 ID や旧レイアウトを現行ノードとして誤読するためである。`docidx` は issue #172 で archive へ退避され、v1→v2 cutover 後の現行処理からは除外した。

meta.json で構造的に候補を絞ってから本文を読む方式は、検索結果を会話へ丸ごと取り込むことで文脈を消費する問題を避けるために採った。外部 FTS 索引はリポジトリを変更しないが非冪等であるため、同じ source を繰り返し index しない。本文の現行契約には対象、順序、read-only 境界だけを残し、索引の重複や stale meta の復旧手順は troubleshooting に分離した。
