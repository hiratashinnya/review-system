# Issue #41「reconciliation: Step2 を docidx surgical read 化（対策A）」

- URL: https://github.com/hiratashinnya/review-system/issues/41
- 状態: closed
- 本文: 685文字、24行。全文スナップショット: `../raw/issues-2026-06.jsonl`
- AC: 総0、未チェック0（本文のチェックボックス表記に限る）
- 関連番号: Issues 検出なし / PRs 検出なし
- 主見出し: ## 背景 | ## 対策（A） | ## 効果見込み | ## 担当ブランチ
- 判定（一次）: E（Closed：履歴保全。現在の運用指示には使わず）

## 本文中の状態・依存記述（最大7件）
- `reconciliation` エージェントのトークン消費が過大。原因は `.claude/agents/reconciliation.md` の **Step 2「合成グラフ構築」**が「既存本ファイル群を Read/Grep して現在のグラフを把握する」と指示しており、毎回 `doc-system/` 配下を丸読みするため。

## 点検メモ
- 本文全体を文字列走査し、AC・状態断言・参照関係を抽出。引用時点の歴史的記述を現行事実と取り違えない。
- 関連Issue／PRの最新状態と実コードとの突合は横断工程で行う。未実施の検証を合格扱いしない。
