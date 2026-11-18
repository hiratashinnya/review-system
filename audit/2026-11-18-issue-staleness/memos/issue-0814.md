# Issue #814「[CI] 単独PRのmaintainability baseline競合を3-way意味的マージで自動修復する」

- URL: https://github.com/hiratashinnya/review-system/issues/814
- 状態: closed（2026-11-18取得）
- 本文: 5196文字/ 85行。全文: `../raw/issues-2026-11.jsonl`
- AC: 13件（未チェック: 0）
- Issue参照: #711, #727, #608, #539, #745
- PR参照: #727
- 主見出し: ## 目的・背景 | ## スコープ・原則 | ## 期待する仕様（最小3-way merge） | ## 実装対象候補 | ## Acceptance criteria | ### 正常系・意味的統合 | ### 非対応・安全停止 | ### テスト・観測・運用 | ## 非目標 | ## 依存・関係
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- Issue #711（PR #727、2026-11-09完了）の `deterministic-conflict-repair` を**単独 OPEN PR の `maintainability_lint/baseline.json` に限定して拡張**する。main と PR が別々の既存保守性負債を解消・更新した際、共通 JSON で生じる機械的なコンフリクトを、未承認の負債を作らず自動解消する。人手での JSON 衝突解消と再生成の繰り返しを減らす
- 1. 対象は現行 #711 と**同じ単独 OPEN PR 判定**を満たす同一repo内PRのみ。main更新時の `push` と PR番号指定 `workflow_dispatch` を利用する。stacked PRの親・子・孫・兄弟、fork、曖昧なPR関係は従来どおり検出・報告のみ（pushなし）。
- 7. 対象PRのOPEN/repo/ref/単独性、live base/head OID を push直前に再取得し、変更があれば廃棄。通常non-force pushのみ。最終PR merge、force push、default branch直接push、自動retargetは実施しない。
- - [x] 実リポジトリの検証専用単独draft PR（mainへのmerge禁止）で、手動dispatchによるbaseline競合の修復、再実行no-op、修復後OIDのchecksを実測し、結果を本Issueへ記録。main pushによる自動修復は通常のmain更新に合わせて実測し、未実測なら該当ACを未チェックにする。既存業務PRを検証用に破損させない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
