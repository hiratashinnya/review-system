# Issue #620「defect_metrics の既存挙動を維持して責務を分割し、maintainability baseline 負債を解消する」

- URL: https://github.com/hiratashinnya/review-system/issues/620
- 状態: closed（2026-11-18取得）
- 本文: 3355文字/ 61行。全文: `../raw/issues-2026-10.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #370, #368, #488, #489, #493, #539, #608
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 互換性・移行・rollback | ## Dependencies / Related issues | ## 実施順の推奨（AI分析・着手日の確定ではない） | ## Project fields
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 2026-10-12のmaintenance lint baselineとopen Issueの照合を5領域＋横断の6サブエージェントでレビューした。関連Issueが高優先でも既存機能の利用だけなら、そのコードの先行分割が既存Issueの必須成果になるわけではない。今回、オーナーが先行可能な整理を別途起票するよう明示指示したため、挙動維持の保守成果として管理する。
- - Blocked by: なし。関連する機能改修の完了待ちを新たに追加しない。
- 4単位の推奨順は defect_metrics → feedback_ledger paths/store → ci_anomaly_report collector → guidance_sync。これは技術的blocked-byではない。対象・baseline・共有テストを同時編集する場合は統合順を合わせる。既存5施策DAGや保留判断を上書きしない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
