# Issue #298「PR merge command送信直前にblockerをfail-closeするpre-use gateを実装する」

- URL: https://github.com/hiratashinnya/review-system/issues/298
- 状態: closed（2026-11-18取得）
- 本文: 3159文字/ 93行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 16件（未チェック: 16）
- Issue参照: #296, #295, #293, #294, #273
- PR参照: なし
- 主見出し: ## 目的 | ## 方針 | ## 既存資産 | ## Managed merge inventory | ## Pre-use flow | ## Fail-close | ## Evidence | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- open blocker、closure violation、cycle、曖昧/cross-repo policy不一致、API/permission/parse、pagination/partial、rebind不一致、unknown tool/alias/unreadable input、auto-merge、hook未登録/無効/untrusted/未発火。
- - [ ] parent/open child と same-PR child close を検証
- - Blocked by: #296

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
