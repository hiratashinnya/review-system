# Issue #470「project-status-sync の初回 dry-run を確認して cron を有効化する（#460 の成果を実稼働させる）」

- URL: https://github.com/hiratashinnya/review-system/issues/470
- 状態: closed（2026-11-18取得）
- 本文: 3240文字/ 50行。全文: `../raw/issues-2026-09.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #460, #465, #466, #461
- PR参照: #465
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - **cron 有効化時の既知の注意点（PR #465 の実装担当が記録）**：`schedule` で発火した run では `inputs.apply` が**空文字**になる。現在の実装は `[ "${APPLY:-false}" = "true" ]` で判定するため空文字は dry-run 側に倒れる。つまり **schedule を足すだけでは cron 実行が永久に dry-run になる**。cron 経路で `--apply` を付ける
- - #466（`stateReason` が `DUPLICATE` / `null` で `UNKNOWN` になる件）の処置。ただし初回 dry-run で `ISSUE_STATE_UNKNOWN` による abort が観測された場合は、#466 の処置が本 Issue の前提になる。
- - **#460（Project Status の自動同期）／PR #465**：本 Issue の前提。PR #465 の merge 後に着手する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
