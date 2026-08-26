# analysis-author — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/analysis-author.md`](../agents/analysis-author.md) にある。

analysis 層では TERM の分析ファセットと design-author の設計ファセットを同一ノードへ段階的に追記する。これは用語の重複ノードを作らず、分析と設計の責務を分離するための運用である。TERM の共有は issue #87 以降の設計で、分析段階で Python 型や定義モジュールを先取りしない。

v2 の slug は path に依存しないグローバル ID である。削除済みノードと同義の概念を再導入する際に旧タイトルへ戻すと、reconciliation-validator が既存 slug の衝突として止める。本文では現行の slug 一意契約だけを示し、再導入時の確認と衝突からの復旧は troubleshooting に分離した。
