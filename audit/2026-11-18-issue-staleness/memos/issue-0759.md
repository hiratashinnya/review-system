# Issue #759「[Maintainability G-03] worktree sweep・残留判定を分離して負債ゼロ」

- URL: https://github.com/hiratashinnya/review-system/issues/759
- 状態: closed（2026-11-18取得）
- 本文: 1686文字/ 33行。全文: `../raw/issues-2026-11.jsonl`
- AC: 4件（未チェック: 0）
- Issue参照: #745, #788, #758, #559, #409, #694, #789
- PR参照: #789, #788
- 主見出し: ## 親・PR単位 | ## リファクタリング対象 | ## 処置 | ## PR専用AC | ## Blocked by | ## Related / 整合対象 | ## 独立レビュー合格記録（2026-11-08）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 着手前提: 直前PRの成果を下段に置き、公開契約を固定してからstackする。
- ## Blocked by
- ※native sub-issueを親 #745 に設定済み。Issue間の正式な依存は上記 Blocked by に従いnative設定済み。既存PRのmain統合前提は本文に従う。
- - PR #788は下段Draft/open。通常merge commit後のPR #789のbase/差分/CI再検証は**未実施・別工程**。親#745の全件完了・baseline空は未達。本Issueをcloseしない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
