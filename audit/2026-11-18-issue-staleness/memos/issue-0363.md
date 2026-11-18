# Issue #363「blocker-snapshot の cron が5分間隔で起動せず（実測74〜104分）、snapshot が常に staleness 上限超過で gate が機能しない」

- URL: https://github.com/hiratashinnya/review-system/issues/363
- 状態: closed（2026-11-18取得）
- 本文: 4527文字/ 109行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #359, #345, #293
- PR参照: #359
- 主見出し: ## 目的・背景 | ## 現状と根拠（実測・2026-08-12） | ### 起動実績 | ### 現在の snapshot の古さ | ### 何が起きるか | ### なぜ起きるか | ### 観測の限界 | ## Scope | ### 選択肢（AI 整理・決定はオーナー） | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（実測・2026-08-12）
- ### 現在の snapshot の古さ
- | **A. `issues` イベント trigger を追加する** | `opened`/`edited`/`closed`/`reopened`/`labeled` 等で起動 | cron に依存しない。Issue に触れば即更新される | **依存関係の追加（`blocked_by` 追加）は Actions の trigger にできない**（#345 で確認済み）。最も危険な遷移を捕捉できない |
- | **E. 現状を受容し、リモート環境では `/issue-pipeline` を使わない** | — | 何もしない | #345 が未解決のまま残る。#345 の受け入れ条件を満たさない |
- - Blocked by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
