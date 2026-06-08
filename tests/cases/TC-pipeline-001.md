---
id: TC-pipeline-001
version: 1.0
---
# P1 通し（受付→合成→評価→検証・仕分け→レポート）

> 対象：`review_system.core.pipeline`（[06 オーケストレーション](../../docs/design/06-orchestration.md)）。
> 非決定（LLM）は `FakePlatformAdapter`（record/replay）で決定化＝アダプタ境界＝テスト境界（E）。

## 目的
P1 の価値経路（出すと 🤖/✋/💬/❓ に仕分けたレポートが返る）が、段の直列＋fail-close で通ることを確認する。

## 手順
`python -m unittest -v tests.unit.test_pipeline_e2e`

## 期待結果
| # | シナリオ | 期待 |
|---|---|---|
| 1 | 正常（valid auto＋judgment＋ghost rule_id） | `Success(ReviewReport)`：auto1・judge1・unclassified1 |
| 2 | 版スタンプ | `stamp.execution_id` が付き、`criteria_content_hash` が入る（S6・再現性） |
| 3 | 保存則 | auto+approve+judge+unclassified = 評価が出した item 総数（取りこぼしゼロ・S1） |
| 4 境界 | doc_type 未解決（型上書きなし） | `Failure`（fail-close・INTAKE・S3） |
| 5 境界 | 基準ゼロ（criteria 空） | `Failure`（fail-close・COMPOSE・スコープ未解決） |
| 6 | 参照除外 | 参照集合のパスの finding はレポートに出ない |
