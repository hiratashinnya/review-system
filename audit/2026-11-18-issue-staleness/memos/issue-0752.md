# Issue #752「[Maintainability I-01] SubagentStop判定・進行ポインタを分離」

- URL: https://github.com/hiratashinnya/review-system/issues/752
- 状態: open（2026-11-18取得）
- 本文: 950文字/ 28行。全文: `../raw/issues-2026-11.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #745, #696, #722, #714, #694, #513
- PR参照: #696
- 主見出し: ## Parent・PRスコープ | ## リファクタリング対象 | ## 処置方針 | ## 専用Acceptance Criteria | ## Blocked by | ## Related / 整合対象（クローズ待ちではない）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 開始条件: PR#696合流、および#722の回帰契約確定
- - [ ] 100000個の開き角括弧を含むactive.json入力でもfail-openせず、規定のdecision:block・終了0を返す。
- ## Blocked by
- ※native sub-issueを親 #745 に設定済み。Issue間の正式な依存は上記 Blocked by に従いnative設定済み。既存PRのmain統合前提は本文に従う。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
