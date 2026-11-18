# Issue #755「[Maintainability I-04] worktree ledger状態遷移・残留検出を分離」

- URL: https://github.com/hiratashinnya/review-system/issues/755
- 状態: open（2026-11-18取得）
- 本文: 976文字/ 29行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #745, #696, #559, #754, #409, #662, #694
- PR参照: #696
- 主見出し: ## Parent・PRスコープ | ## リファクタリング対象 | ## 処置方針 | ## 専用Acceptance Criteria | ## Blocked by | ## Related / 整合対象（クローズ待ちではない）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 開始条件: PR #696統合済み、直前段のコード契約確定・stack上段作成。
- open/bind/mark/noteとdeferred release、未解放/孤児worktreeの検出・掃除に分け、元ファイル100行以内。
- ## Blocked by
- ※native sub-issueを親 #745 に設定済み。Issue間の正式な依存は上記 Blocked by に従いnative設定済み。既存PRのmain統合前提は本文に従う。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
