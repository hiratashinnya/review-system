# Issue #719「isdigit() と int() の併用で非 ASCII 数字・巨大桁が ValueError の Traceback になる（karte 以外: codex_worktree_exec・branch_source）」

- URL: https://github.com/hiratashinnya/review-system/issues/719
- 状態: closed（2026-11-18取得）
- 本文: 4400文字/ 76行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 0）
- Issue参照: #696
- PR参照: #696
- 主見出し: ## 対象 harness | ## 目的・背景 | ## 現状と根拠 | ### 同型だが harm: none と見立てた箇所（確認対象） | ### 再現手順・期待結果・実際結果 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- | 箇所 | 現在のコード | 入力 | 現在の挙動 | 期待 |
- 3. 期待結果は上表の「期待」列、実際結果（コード読み）は「現在の挙動」列。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
