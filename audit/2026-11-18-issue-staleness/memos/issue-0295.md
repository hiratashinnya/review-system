# Issue #295「blocker gateのpre-use policy・実行順序・fail-close制御を設計する」

- URL: https://github.com/hiratashinnya/review-system/issues/295
- 状態: closed（2026-11-18取得）
- 本文: 3385文字/ 107行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 11件（未チェック: 11）
- Issue参照: #299, #296, #293, #294, #300, #5, #273
- PR参照: なし
- 主見出し: ## 目的 | ## オーナー確定方針 | ## 現状根拠 | ## 設計対象 | ## Control flow | ## 実行順序不変条件 | ## Result / logs | ## Acceptance criteria | ## Out of scope | ## Dependencies / Related
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - blocked-by は実行順、parent/sub-issue は包含、related は参照。
- - native blocked-by を dependency 正本とする。
- - open child を残す parent close は拒否し、same-PR child close は仮想状態で評価。
- - `BLOCK`: open blocker / closure violation。deny。
- - Native blocked-by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
