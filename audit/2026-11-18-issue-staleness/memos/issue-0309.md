# Issue #309「feat(hooks): SubagentStart でカルテ手順を注入し SubagentStop で未更新をブロックする」

- URL: https://github.com/hiratashinnya/review-system/issues/309
- 状態: closed（2026-11-18取得）
- 本文: 4233文字/ 104行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #307, #308, #310, #192, #129
- PR参照: なし
- 主見出し: ## 目的・背景 | ### 利用者価値 | ## 現状と根拠 | ## 提案挙動 | ### `.claude/hooks/inject-karte-protocol.sh`（SubagentStart / matcher `issue-fixer`） | ### `.claude/hooks/require-karte.sh`（SubagentStop / matcher `issue-fixer`） | ### 実装様式（既存踏襲） | ## 互換性 | ## 代替案 | ## Scope | ## Out of scope | ## Acceptance criteria
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `.claude/settings.json` は現在 `PreToolUse` / `PostToolUse` / `StopFailure` / `UserPromptSubmit` /
-   「入力が検査不能なら deny」と同じ扱いで、他の助言系フック（fail-open）とは方針を変える。
- - ブロック時も **`exit 0` ＋ JSON 本文**で返し、既存テストハーネスの `check=True` 前提を壊さない。
- - [ ] ブロック時も終了コードは 0（既存テストハーネスの `check=True` 前提を壊さない）。
- - blocked by #307（`karte check` を呼ぶため）
- - blocked by #308（matcher 対象の `issue-fixer` が存在している必要があるため）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
