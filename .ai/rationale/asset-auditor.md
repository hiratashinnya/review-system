# asset-auditor — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/asset-auditor.md`](../agents/asset-auditor.md) にある。

asset-auditor と spec-inspector を分けたのは、前者が AI 資産の責務・重複・起動競合を監査し、後者が I/O・イベント・DFD・schema の仕様整合性を監査するためである。生成と点検を一つのロールへ混ぜないことで、既存資産を再利用する判断を独立させる。

context-mode の索引は候補発見の補助に過ぎず、リポジトリへの著作権限を与えない。外部索引が非冪等であるため、同一 source の重複登録を避けるという注意は troubleshooting 側へ移した。

## Grep/Glob 削除の検討と却下（Issue #535・2026-09-27）

GATED_ROLES（issue-fixer/issue-implementer/pr-reviewer）で Grep/Glob が実効配布されないことが実測で
確認され、その是正の一環として本ロールからも一旦削除する変更が提案された。しかし本ロールは
GATED_ROLES に属さず isolation 指定も無く、GATED_ROLES の実測結果が本ロールに当てはまるかは
実測されていなかった。**この実効配布漏れの原因は GATED_ROLES 所属と Bash 保有の双方で交絡しており、
特定できていない**（F-535-21・詳細は [`.ai/rationale/issue-fixer.md`](issue-fixer.md)「ctx_search/ctx_index
の付与根拠」を参照）。本ロールは Bash を保有しないため、原因が Bash 保有側にあるとしても本ロールには
当てはまらない可能性がある一方、GATED_ROLES 非所属である以上 GATED_ROLES 側の原因も当てはまらない
可能性がある——いずれにせよ根拠なく削除を決めるには実測が不足していた。ctx_search は BM25 の
上位k件しか返さず、Grep の網羅的な正規表現検索・Glob のファイル列挙の代替にならないため、
実測不足のまま削除すると資産監査の網羅性が退化するおそれもあった。オーナー判断により削除を却下し、
Grep/Glob と ctx_search/ctx_index を両方保持することにした。
