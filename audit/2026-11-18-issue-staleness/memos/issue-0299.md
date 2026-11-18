# Issue #299「blocker gate hook・merge経路・policy driftを継続監査する」

- URL: https://github.com/hiratashinnya/review-system/issues/299
- 状態: closed（2026-11-18取得）
- 本文: 2368文字/ 69行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 14件（未チェック: 14）
- Issue参照: #297, #298, #293, #5, #273
- PR参照: なし
- 主見出し: ## 目的 | ## 根拠 | ## 提案 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- unknown merge path、hook未発火、manifest不一致、expired waiver、closed parent+open child、relation/display矛盾はfail-close/owner actionとし、警告だけで完了扱いにしない。
- - [ ] cycle、closed parent+open child、body/Project driftを一覧化
- - Blocked by: #297, #298

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
