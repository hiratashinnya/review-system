# Issue #294「GitHub blocker・sub-issue・PR closing Issue APIと無料gate構成を検証する」

- URL: https://github.com/hiratashinnya/review-system/issues/294
- 状態: closed（2026-11-18取得）
- 本文: 2271文字/ 61行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 0）
- Issue参照: #300, #295, #297, #298, #299, #296, #293, #273
- PR参照: #300
- 主見出し: ## 目的 | ## 調査後のオーナー決定（現在の正本） | ## Issue / PR の終了判定 | ## 調査で確定した入力 | ## Scope / Out of scope | ## Acceptance criteria / 移管 | ## Dependencies / Related
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 調査後のオーナー決定（現在の正本）
- 4. merge invocation ごとに API を fresh readし、PR / head / base / default branch / closing set、blocked-by graph、closure invariant を評価。
- - REST / GraphQL で blocked-by、blocking、parent、sub-issue と pagination を取得可能。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
