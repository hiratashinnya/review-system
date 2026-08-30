# analysis-author — 回復手順（非規範）

slug 衝突、参照先欠落、md/yaml 対の不一致が出た場合は reconciliation へ進めず、対象 slug と参照先を記録して著作を止める。既存ノードの更新であれば、更新対象を hand-off の `update_slugs` に明記して validator へ渡す。新規と判断して同じ slug を別名なしに上書きしない。

削除済み概念の再導入や TERM の設計ファセット追記では、まず corpus の実ファイルと version を確認する。analysis-author が担当する分析ファセットと design-author が担当する設計ファセットを同じ dispatch で推測して補完しない。
