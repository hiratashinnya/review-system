# asset-auditor — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/asset-auditor.md`](../agents/asset-auditor.md) にある。

asset-auditor と spec-inspector を分けたのは、前者が AI 資産の責務・重複・起動競合を監査し、後者が I/O・イベント・DFD・schema の仕様整合性を監査するためである。生成と点検を一つのロールへ混ぜないことで、既存資産を再利用する判断を独立させる。

context-mode の索引は候補発見の補助に過ぎず、リポジトリへの著作権限を与えない。外部索引が非冪等であるため、同一 source の重複登録を避けるという注意は troubleshooting 側へ移した。

## Grep/Glob 削除の検討と却下（Issue #535・2026-09-27）

GATED_ROLES から実効配布されない Grep/Glob を外す是正の一環として、本ロールからも一旦削除する変更が
提案された。しかし本ロールは GATED_ROLES に属さず isolation 指定も無いため、GATED_ROLES 限定の実効
配布漏れという根本原因が本ロールに当てはまるかは実測されていなかった。ctx_search は BM25 の上位k件
しか返さず、Grep の網羅的な正規表現検索・Glob のファイル列挙の代替にならないため、根拠なく削除すると
資産監査の網羅性が退化する。オーナー判断により削除を却下し、Grep/Glob と ctx_search/ctx_index を
両方保持することにした。
