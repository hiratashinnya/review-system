# Issue #758「[Maintainability G-02] worktree collect/release・handoffを分離」

- URL: https://github.com/hiratashinnya/review-system/issues/758
- 状態: closed（2026-11-18取得）
- 本文: 2049文字/ 37行。全文: `../raw/issues-2026-11.jsonl`
- AC: 4件（未チェック: 0）
- Issue参照: #745, #757, #559, #409, #694, #788, #787
- PR参照: #788, #787
- 主見出し: ## 親・PR単位 | ## リファクタリング対象 | ## 処置 | ## PR専用AC | ## Blocked by | ## Related / 整合対象 | ## G-02 実装・検証状況（2026-11-07）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 着手前提: 直前PRの成果を下段に置き、公開契約を固定してからstackする。
- ## Blocked by
- ※native sub-issueを親 #745 に設定済み。Issue間の正式な依存は上記 Blocked by に従いnative設定済み。既存PRのmain統合前提は本文に従う。
- - 実装: Draft PR #788（base は下段 PR #787 の head `stack-g/757-worktree-args-paths`、head `stack-g/758-worktree-collect-release`）。
- - 親 #745 の C01～C04 は PR #788 に証跡記録。**C05 は独立レビュー合格**（[PR #788 Round 1 clean カルテ](https://github.com/hiratashinnya/review-system/pull/788#issuecomment-6720652895)、対象HEAD `4659a8c`、重大指摘0・open finding 0）。本IssueのPR専用ACは充足。**親 #745 の全体

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
