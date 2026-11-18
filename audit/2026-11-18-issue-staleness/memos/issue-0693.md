# Issue #693「project_status_sync の計画生成・レポート表示を責務分割し、maintainability baseline 負債を解消する」

- URL: https://github.com/hiratashinnya/review-system/issues/693
- 状態: closed（2026-11-18取得）
- 本文: 2527文字/ 44行。全文: `../raw/issues-2026-10.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #608, #547, #685, #375, #460, #470, #539, #620, #623
- PR参照: なし
- 主見出し: ## 目的・背景 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 4. 同一の固定入力で、変更前後の `Plan`、`report.json`、summary文字列、異常判定を比較する回帰テストを補う。特に snapshot 不正/鮮度超過、unknown state、OPEN_BLOCKER、closure warning、dry-run/apply、skipped/warnings を保護する。
- - Blocked by: なし。#685（工程dispatch）と #375（reviewer handoff）から独立して進める。ただし並行PRで baseline.json を触るときは最終統合時に別変更を上書きしない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
