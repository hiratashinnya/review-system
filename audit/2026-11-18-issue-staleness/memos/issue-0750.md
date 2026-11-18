# Issue #750「[Maintainability K-05] karte similarity/touchedを責務分離して負債ゼロ」

- URL: https://github.com/hiratashinnya/review-system/issues/750
- 状態: open（2026-11-18取得）
- 本文: 918文字/ 28行。全文: `../raw/issues-2026-11.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #745, #749, #513, #683
- PR参照: なし
- 主見出し: ## 親・PR単位 | ## リファクタリング対象ファイル | ## 実装スコープ | ## Acceptance Criteria（本PR専用） | ## Blocked by（着手/マージ順） | ## Related / 整合すべき既存Issue
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 前提: 直前PRの独立レビュー完了後、そのPRを下段としてstackする。実マージ前には最新版baselineで再検証。
- ## Blocked by（着手/マージ順）
- ※native sub-issueを親 #745 に設定済み。Issue間の正式な依存は上記 Blocked by に従いnative設定済み。既存PRのmain統合前提は本文に従う。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
