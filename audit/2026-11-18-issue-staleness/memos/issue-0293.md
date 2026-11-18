# Issue #293「blocker依存をIssue処理開始時とPR merge command送信前に自動gateする」

- URL: https://github.com/hiratashinnya/review-system/issues/293
- 状態: closed（2026-11-18取得）
- 本文: 5946文字/ 113行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 18件（未チェック: 1）
- Issue参照: #294, #295, #296, #297, #298, #299, #5, #273
- PR参照: なし
- 主見出し: ## 目的 | ## オーナー確定方針 | ## 既存資産の根拠 | ## Flow | ## Sub-issues | ## Acceptance criteria | ## Dependencies / Related | ## Harness | ## 【調査結果・AC更新記録】（Claude Code (AI)・2026-09-05） | ### 実装済みと確認した11項目（エビデンス） | ### 未達成と判定した1項目 | ### この状態で#293をクローズする根拠
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- blocked-by を記憶や目視で管理せず、次の管理対象操作の直前に同一 policy core で fresh 判定し、未解決 blocker または判定不能なら fail-close する tracking Issue である。
- - closing set に post-merge 仮想状態を適用し、native blocked-by graph と parent/sub-issue closure invariant を評価する。
- - reviewer は現在 `gh pr merge` を許可するが、blocker API 判定は未実装。
- - [x] open child を残す parent close を拒否し、same-PR child close は仮想状態で評価
- | blocker/曖昧/API error/pagination/cycle/識別不能で fail-close | `blocker_gate/model.py` の正準 reason 集合に `OPEN_BLOCKER`／`CLASSIFIER_UNKNOWN`／`API_PERMISSION`／`API_UNREACHABLE`／`PAGINATION_INCOMPLETE`／`GRAPH_CYCLE` が実在し、各々 `blocker_gate/{
- | open child残しparent close拒否・same-PR child closeの仮想評価 | `blocker_gate/evaluator.py`「`CLOSED(parent) => all descendants CLOSED` を dependency と独立評価」＋ `closing.py` の `build_delivered_messages`（仮想 closing set 構築） |

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
