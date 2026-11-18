# Issue #9「frontmatter パーサのデッドコード分岐を整理（list item の mapping/scalar 2分岐）」

- URL: https://github.com/hiratashinnya/review-system/issues/9
- 状態: closed
- 本文: 724文字、23行。全文スナップショット: `../raw/issues-2026-06.jsonl`
- AC: 総2、未チェック2（本文のチェックボックス表記に限る）
- 関連番号: Issues #2 / PRs #2
- 主見出し: ## 指摘元 | ## 問題 | ## 方針（案） | ## 受け入れ条件
- 判定（一次）: E（Closed：履歴保全。現在の運用指示には使わず）

## 本文中の状態・依存記述（最大7件）
抽出なし

## 点検メモ
- 本文全体を文字列走査し、AC・状態断言・参照関係を抽出。引用時点の歴史的記述を現行事実と取り違えない。
- 関連Issue／PRの最新状態と実コードとの突合は横断工程で行う。未実施の検証を合格扱いしない。
