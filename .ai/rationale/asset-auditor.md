# asset-auditor — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/asset-auditor.md`](../agents/asset-auditor.md) にある。

asset-auditor と spec-inspector を分けたのは、前者が AI 資産の責務・重複・起動競合を監査し、後者が I/O・イベント・DFD・schema の仕様整合性を監査するためである。生成と点検を一つのロールへ混ぜないことで、既存資産を再利用する判断を独立させる。

context-mode の索引は候補発見の補助に過ぎず、リポジトリへの著作権限を与えない。外部索引が非冪等であるため、同一 source の重複登録を避けるという注意は troubleshooting 側へ移した。
