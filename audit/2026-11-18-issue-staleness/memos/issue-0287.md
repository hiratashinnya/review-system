# Issue #287「Q27: 複数 finding 修正で workspace 更新が上書き消失しないようにする」

- URL: https://github.com/hiratashinnya/review-system/issues/287
- 状態: open（2026-11-18取得）
- 本文: 1861文字/ 70行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #268, #273
- PR参照: #268
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Bug characterization | ### 再現手順 | ### 期待する結果 | ### 実際の結果 | ### 確認環境 | ### 影響
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- PR #268 の実装照合で、`suggested_fix` は差分ではなく修正後 file 全文を表し、複数 finding が同じ file を更新すると古い全文で先行修正を消す可能性がある。現在はこの消失を検知せず Success とできる余地がある。
- `suggested_fix` が差分ではなく修正後 file 全文であるため、B の古い全文が A の変更を上書きして消失させうる。現状はこの消失を検知せず、finding 単位では Success と扱える余地がある。
- 各 finding の `suggested_fix` を独立した完全 snapshot として生成する一方、適用時に現在の workspace version、共通 base、同一 file の複数 writer を照合していない可能性が高い。楽観的 concurrency control、三方 merge、または file 単位の一括計画が欠けているかを確認する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
