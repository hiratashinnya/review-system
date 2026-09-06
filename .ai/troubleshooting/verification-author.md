# verification-author — 回復手順（非規範）

FND、DD、Q、PEND の path status と edges が食い違った場合は、著作段で status フィールドを足したり辺を手で反転したりせず、対象 node と現行 config の status_dirs を確認する。FND の解消は reconciliation の reverse 操作へ戻す。

config の接続規則を変更した DD/FND で著作資産の同期先が不明なら、変更型、旧辺、新辺、確認した資産を列挙して STOP する。接続マトリクスや author 本文を推測で一括修正しない。
