# Issue #628「agy 実効設定と WSL 起動の実測根拠を取得し、agy-delegate ラッパーの fail-close 停止を解除する（#606 finding (1) 申し送り・#575 の子）」

- URL: https://github.com/hiratashinnya/review-system/issues/628
- 状態: closed（2026-11-18取得）
- 本文: 2602文字/ 54行。全文: `../raw/issues-2026-10.jsonl`
- AC: 8件（未チェック: 0）
- Issue参照: #680, #627, #607, #679, #606, #575, #271, #284, #290, #513
- PR参照: #680, #627
- 主見出し: ## 目的・背景 | ## 起票時の現状と根拠（履歴） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 起票時の現状と根拠（履歴）
- - PR #627（draft）に直接実行ラッパー `agy_delegate/`・`.ai` 正本・許可設定の read-only 検査・規範更新が入っている。通常 `run` は設定層・起動環境が未確認のため子プロセスを起動しない（意図的）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
