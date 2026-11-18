# Issue #64「[doc-system] backref check 既存 18 ERROR の是正（FND ライフサイクル不整合・main 由来）」

- URL: https://github.com/hiratashinnya/review-system/issues/64
- 状態: closed（2026-11-18取得）
- 本文: 1172文字/ 28行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #61
- PR参照: #61
- 主見出し: ## 背景 | ## 内訳（3カテゴリ） | ### A. open-but-backref-exists（8件）＝open だが対象に →FND 辺あり（辺逆転未完） | ### B. resolved-no-dd3（6件）＝resolved だが本文に「**指摘時 ref_version**:」記録が無い（DD-3 違反） | ### C. resolved-no-backref（4件）＝resolved だが backward 辺（→FND）が無い | ## スコープ | ## 備考
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ### A. open-but-backref-exists（8件）＝open だが対象に →FND 辺あり（辺逆転未完）
- - A：辺逆転を完了する（open のまま backref を残さない）か、当該 FND を resolved 化する（`backref reverse` で機械実行）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
