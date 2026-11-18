# Issue #567「CI: Node.js 20 非推奨警告の解消（setup-python@v5 ほか Node 24 対応版へ更新）」

- URL: https://github.com/hiratashinnya/review-system/issues/567
- 状態: closed（2026-11-18取得）
- 本文: 2632文字/ 58行。全文: `../raw/issues-2026-10.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: なし
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 保守・アップグレード情報 | ## Dependencies / Related issues | ## Project fields（実行環境の制約により一部自動設定できず・要手動設定）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- GitHub Actions の実行ログに「Node.js 20 is deprecated. ... forced to run on Node.js 24」という警告が出ている。現状は Node 24 で強制実行されて動作しているが、対象 action を Node 24 対応版へ更新し、警告を解消する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
