# Issue #812「gh-create-issue エージェントの文書が許可すると読める gh の使い方を command gate が拒否している（許可・拒否の一覧が文書にない）」

- URL: https://github.com/hiratashinnya/review-system/issues/812
- 状態: closed（2026-11-18取得）
- 本文: 8686文字/ 115行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 0）
- Issue参照: #810, #697, #375, #800, #342, #227, #269, #694, #849, #632
- PR参照: #697, #849
- 主見出し: ## 対象 harness | ## 目的・背景 | ## 現状と根拠 | ### 文書側の記述（main `a3a2d4a` で確認） | ### 観測した食い違い（再現状況つき） | ### gate の実際の許可（コード確認・main `a3a2d4a`） | ### テストとの関係 | ## Scope | ### 選択肢 | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- 再現状況の表記：**【実測】**＝起票時（2026-11-11）に `gh-create-issue` ロール自身の Bash で実行し、gate の判定を確認した。**【コード確認】**＝main `a3a2d4a`（2026-11-10）の `.claude/hooks/agent-command-gate.sh`（`gh_create_issue_violation` ほか）を読んだ。**【申告】**＝#810 起票 run のエージェント最終報告。
- ### 観測した食い違い（再現状況つき）
- | # | 文書から「使える」と読める使い方 | gate の判定 | 再現状況 |
- - #694（open）：項目 11(f)(g) などで同じロールの実行環境の摩擦が記録されている。ただし本 Issue は文書と gate の許可範囲の食い違いの是正で、#694 は信頼境界・実行環境の観測を束ねた Issue。本 Issue の文書整合は #694 の判断に依存せず、別軸として扱う。
- - #269（open）：gate を MCP へ拡張する Issue。allowlist 方式の原則の出典として参照する。
- - #810（open）：観測の契機（起票 run）。
- - parent／sub-issue／blocked-by：なし。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
