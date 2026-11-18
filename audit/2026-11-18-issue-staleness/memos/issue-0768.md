# Issue #768「[Maintainability L-01] feedback_ledgerの検証と状態集計を分離」

- URL: https://github.com/hiratashinnya/review-system/issues/768
- 状態: open（2026-11-18取得）
- 本文: 1059文字/ 30行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #745, #724, #523, #524, #525
- PR参照: なし
- 主見出し: ## 親・PR単位 | ## リファクタリング対象ファイル | ## 処置内容 | ## PR専用Acceptance Criteria | ## Blocked by | ## Related / 整合対象
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 開始条件: mainのbaseline再計測。karte/issue_start/gitgate/blocker_gateとは別領域のため調査・設計は並行可。
- ## Blocked by
- - なし。既存Issueのクローズを一括前提としない。
- ※native sub-issueを親 #745 に設定済み。Issue間の正式な依存は上記 Blocked by に従いnative設定済み。既存PRのmain統合前提は本文に従う。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
