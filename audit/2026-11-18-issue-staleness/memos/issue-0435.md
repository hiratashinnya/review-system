# Issue #435「pr_merge_gate/audit.py: audit.jsonl運用改善（破損行可視化・件数ローテーション・PR番号相関・classifier誤ブロック緩和）」

- URL: https://github.com/hiratashinnya/review-system/issues/435
- 状態: closed（2026-11-18取得）
- 本文: 5013文字/ 113行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #433, #436, #414, #442, #428, #429, #430, #431, #434
- PR参照: #433, #442
- 主見出し: ## 目的・背景 | ## Scope | ### 項目1：壊れた監査ログ行の読み飛ばしを可視化する（元#435・PR #433 finding F-414-02） | ### 項目2：audit.jsonlの件数ベースローテーション（Issue #436より・オーナー承認済み） | ### 項目3：PreToolUse/PostToolUseの相関チェックをPR番号ベースに簡素化（Issue #436より・オーナー承認済み） | ### 項目4：CLASSIFIER_UNKNOWN誤ブロックの緩和（Issue #436より・オーナー承認済み） | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 現状: `pr_merge_gate/audit.py::append_completion` は壊れた行（`json.JSONDecodeError`）に
-   は現状「merge操作だと再分類できた場合のみ」完了記録を書く分岐に入り、それ以外のBashコマンドは

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
