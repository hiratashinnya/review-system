# Issue #437「karte close-attempt の diff 計算が isolated worktree の cwd を解決できず spurious に fail-close する（実測 touched-set が常に空になる）」

- URL: https://github.com/hiratashinnya/review-system/issues/437
- 状態: closed（2026-11-18取得）
- 本文: 4838文字/ 72行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #307, #355, #426, #309, #315, #354, #330
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠（再現事実） | ## 再現手順 | ## 期待結果 | ## 実際結果 | ## 環境 | ## 影響 | ## root cause 仮説 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（再現事実）
- `karte/touched.py::git_diff` が `repo_root` に `karte.paths.main_worktree_root()`（台帳ファイルの所在解決には正しい・複数 worktree 間で共有する単一の正本パス）をそのまま流用している。台帳（ledger）は worktree 間で共有すべき単一の正本だが、**diff は worktree ごとに独立した値**であり、同じ関数で解決してはならない。`isolation: 
- - Related: #315（karte の実測信号の強制点・自動 resolved の fail-open）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
