# Issue #491「codex CLI の feature catalog 更新に追随できず、codex 導入済みローカルで test_codex_supervisor が常に error になる」

- URL: https://github.com/hiratashinnya/review-system/issues/491
- 状態: closed（2026-11-18取得）
- 本文: 4231文字/ 92行。全文: `../raw/issues-2026-09.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #488, #490, #431
- PR参照: #490
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## root cause 仮説 | ## 影響 | ## 提案挙動（選択肢・比較・推奨） | ## Scope | ## Out of scope | ## 互換性 | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（未設定項目・手動設定が必要）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `validate_cli_compatibility` の呼び出し側の契約（例外型・エラーコード）は変えない前提。エラーコードを増減する場合は呼び出し側の分岐も併せて確認する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
