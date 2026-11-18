# Issue #743「[bug][CI][#711 blocker] conflict_repair が古い PR base.sha を最新 main OID と比較して単独PRを誤除外する」

- URL: https://github.com/hiratashinnya/review-system/issues/743
- 状態: closed（2026-11-18取得）
- 本文: 3860文字/ 52行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #711, #727, #42023465203, #733, #451, #41563573379, #696, #697, #716, #717
- PR参照: #727, #733, #451, #717
- 主見出し: ## 問題・実害 | ## 原因（コード確認済み） | ## 要求する修正 | ## Acceptance criteria（PR単位で検証可能） | ## Scope / 非目標 | ## 依存関係
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- Issue #711 / PR #727 で実装・main反映した `deterministic-conflict-repair` が、**既存OPEN PRの `base.sha` が現在の `main` より古いだけで `branch OID 不一致` と判定し、単独PRの生成guidance競合・drift修復を一切評価できない**。
- - `conflict_repair/runner.py` の `evaluate()` がそれをbase OIDとして `api.branch_oid(base)`（現在のbranch tip）と比較し、不一致なら早期returnする。
- - OPEN PRの `base.sha` と最新branch先端が一致することは保証できない。main更新を契機とする機能なのに、通常のmain先端更新を異常として扱ってしまっている。
- 1. PR APIの `base.ref` / repo / OPEN / head / stacked関係を**対象の識別**に使い、処理対象のbase OIDには**現在のdefault branch tipをliveに取得した値**を使う。PR API `base.sha` は最新branch tipの必須一致条件にしない。
- 3. push直前にOPEN・base/head ref・repo・単独/stacked関係・現在base tip OIDとhead OIDを再照合する。途中の変更はfail-closed（pushなし）。既存のnon-force / expected remote headチェックは維持。
- - [ ] **正常系・stale base.sha**：PR API `base.sha` が旧OID、live `main` は新OIDの単独OPEN PRを実Git＋制御可能APIで再現し、最新mainの内容を取り込んだ上で修復の必要性を評価できる。base SHAの陳腐化のみを理由にskipしない。
- GitHub nativeのblocked-by関係は可能なら **#711 blocked by 本Issue** と設定する。本Issue自体は#716にブロックされない（既に完了）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
