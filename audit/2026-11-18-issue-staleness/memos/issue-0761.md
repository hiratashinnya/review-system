# Issue #761「[Maintainability G-05] branch_source/policy.pyを責務分離して負債ゼロ」

- URL: https://github.com/hiratashinnya/review-system/issues/761
- 状態: closed（2026-11-18取得）
- 本文: 1848文字/ 34行。全文: `../raw/issues-2026-11.jsonl`
- AC: 4件（未チェック: 0）
- Issue参照: #745, #740, #741, #719, #760, #565, #794, #791
- PR参照: #794
- 主見出し: ## 親・PR単位 | ## リファクタリング対象 | ## 処置 | ## PR専用AC | ## Blocked by | ## Related / 整合対象 | ## 独立レビュー・CI確定結果（G-05 / 2026-11-09）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 着手前提: 直前PRの成果を下段に置き、公開契約を固定してからstackする。
- ## Blocked by
- ※native sub-issueを親 #745 に設定済み。Issue間の正式な依存は上記 Blocked by に従いnative設定済み。既存PRのmain統合前提は本文に従う。
- - **下段 #791 未マージ、#794 Draft継続。** 下段通常merge後のbase/差分/CI再確認、Draft解除、PR merge、#761 closeは今回対象外。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
