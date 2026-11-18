# Issue #570「/tmp 配下の worktree で sandbox テストが bwrap: Can't chdir で失敗する原因の切り分け」

- URL: https://github.com/hiratashinnya/review-system/issues/570
- 状態: open（2026-11-18取得）
- 本文: 2291文字/ 61行。全文: `../raw/issues-2026-10.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #542, #538, #452
- PR参照: なし
- 主見出し: ## 種別 | ## 目的・背景 | ## 現状と根拠 | ## 再現手順（分かる範囲。要確認） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Labels / Project fields
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 原因の切り分け（mount／bwrap 引数／テスト前提のどれか）。
- - [ ] 原因が「環境依存」「テストの前提」「sandbox 構成」のいずれかに分類され、根拠（生出力）が付いている。
- - blocked-by は設定しない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
