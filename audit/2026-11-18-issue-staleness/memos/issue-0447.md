# Issue #447「pr_merge_gate: connector分類(_connector_operation)がGitHub MCP serverの実スキーマ(owner/repo/pullNumber)を受理できずCLASSIFIER_UNKNOWNで全merge拒否」

- URL: https://github.com/hiratashinnya/review-system/issues/447
- 状態: closed（2026-11-18取得）
- 本文: 4426文字/ 92行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #446
- PR参照: #446
- 主見出し: ## 目的・背景 | ## 現状と根拠（再現事実・該当path） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 再現手順 | ## 期待結果 | ## 実際の結果 | ## 環境 | ## 影響 | ## root cause 仮説
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（再現事実・該当path）
- 1. Claude Code on the web（Claude Code Remote）環境で、GitHub MCP server の `mcp__github__merge_pull_request` を任意の open PR に対して呼び出す（`owner`/`repo`/`pullNumber`/`merge_method` を指定）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
