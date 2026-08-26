# design-author — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/design-author.md`](../agents/design-author.md) にある。

TERM は analysis-author が作る共有ノードであり、design-author は DM 確定後に設計ファセットだけを追記する。この分担は、同じ用語を分析層と設計層で二重作成する競合を防ぐために決めた。

既存 TERM を同じ slug で tmp に出すと、新規 slug と同じ検査では既存 ID 衝突になる。そこで更新対象を `update_slugs` として validator に明示し、reconciliation には既存ノード更新として渡す方式（案 A、issue #97）を採用した。バッチ内重複や非宣言 slug の衝突はこの例外に含めず、従来どおり fail-close とする。

TERM が存在しない場合に design-author が先に著作すると分析ファセットを失うため、analysis-author の先行を前提にしている。本文の停止条件と hand-off はこの現在の契約だけを規定し、失敗時の照合手順は troubleshooting に置く。
