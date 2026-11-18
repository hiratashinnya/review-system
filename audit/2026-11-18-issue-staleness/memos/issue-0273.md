# Issue #273「PR #259/#260/#268 レビュー指摘・残課題の処置トラッキング」

- URL: https://github.com/hiratashinnya/review-system/issues/273
- 状態: open（2026-11-18取得）
- 本文: 6181文字/ 93行。全文: `../raw/issues-2026-07b.jsonl`
- AC: 17件（未チェック: 17）
- Issue参照: #259, #260, #268, #290, #271, #272, #291, #285, #258, #292, #286, #287, #270, #284, #6, #7, #11, #141
- PR参照: #259, #260, #258, #268
- 主見出し: ## 目的 | ## PR と close 対象 | ## Evidence index（2026-07-29 時点） | ### 追跡規則 | ## Sub-issues | ### PR 成果受入れ | ### 横断・残課題 | ## 実行順と relation | ### PR #260 の default branch 到達 gate | ## Out of scope | ## Close gate | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
-   - blocked by #270、#284
-   - #270 と #284 の close は PR #259 の必須 merge gate。いずれかが open の場合は PR #259 の merge と #290 の close を停止する
-   - blocked by #290
- - [ ] #270 — settings hook の未引用による fail-open を解消する
- 親子 relation は成果の包含、blocked-by は実行順依存、本文中の参照は related として扱います。親子関係だけを blocker とみなしません。
- - closed Issue #6 の reopen（#292 で文書上の対象漏れだけを補完する）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
