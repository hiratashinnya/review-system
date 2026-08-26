# reconciliation — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/reconciliation.md`](../agents/reconciliation.md) にある。

著作→read-only 検証→反映の2段（実行上は3ロール）に分離したのは、検証結果を再解釈して都合のよいノードを反映する経路をなくすためである。全 parent を一括で反映し、いずれかの欠落でバッチ全体を blocked にするのは、部分反映によるグラフ不整合を避けるためである。

FND の status 遷移は ID を変えない rename、辺の反転は dsv2 reverse、tmp の掃除は保護された clean-tmp に限定する。これらは履歴と参照を保つために採用された現在の設計であり、手作業の代替手順を本文へ追加しない。
