# doc-system-v2-authoring — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/doc-system-v2-authoring.md`](../agents/doc-system-v2-authoring.md) にある。

`scheduled` の既定を current phase としつつ、既存ノードの一括 backfill の具体値はオーナーだけが決める。current phase と一致することや機械検証が通ることは、値の妥当性の根拠にならない。この境界は、PR #150 で `scheduled: sprint-1` の 558 件 backfill を、指示側の具体値がないまま current phase 一致を根拠に許容した事例を受けて明文化された（Issue #185）。

新規ノードの既定値設定と既存ノードの値変更を同じ操作に見せないことが再発防止の要点である。明示値がある更新は機械的に実行でき、明示値がない更新は STOP してオーナー確認へ戻す。本文ではこの現在の判定規則だけを残した。
