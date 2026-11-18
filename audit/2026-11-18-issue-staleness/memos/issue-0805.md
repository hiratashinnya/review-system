# Issue #805「docs(karte): model.py 入口の docstring 要約化後、同「改ざん防止の機械的裏付けと既知の限界」節を名指す4文書の参照先を rationale へ更新する（F-799-07）」

- URL: https://github.com/hiratashinnya/review-system/issues/805
- 状態: open（2026-11-18取得）
- 本文: 5260文字/ 84行。全文: `../raw/issues-2026-11.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #799, #747, #363, #522, #745, #804, #746, #748, #683
- PR参照: #799
- 主見出し: ## 対象 harness | ## 目的・背景 | ## 現状と根拠 | ## オーナー判断が必要な選択 | ### 本体の方針（A / B / C） | ### 副論点 D1（A を選ぶ場合）: governance-directives.md の追従履歴コメントの扱い | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 重複調査（起票時・open/closed）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - PR #799（draft・open・base `stack-k/746-model-parse`・head `stack-k/747-model-review`）の入口 docstring は、追記規律と二層保護の要約数行と「全文は `.ai/rationale/karte-module-split.md` の「K-02 実装で移設した docstring（#747）」」だけを持つ。旧 docstring の逐語は、rationale の「K-02 
- | C | 現状維持 | 変更ゼロ。governance を触らない。PR #799 の現行方針そのもの | 見出しは残るので機械的には壊れていないが、「実測の詳細」を求める文書が要約しか見つけられず、読み手が入口で止まる |
- - D1-b: 履歴コメント中の参照先も新しい所在へ書き換える。メリット: 4文書の記述が見た目で揃う。デメリット: 当時の記録が現在の事実と混ざる（PR8 区分1に反する）。
- - Blocked by: PR #799（stack L2・Issue #747 K-02）の merge。着手順序は PR #799 の merge 後。PR を対象にした native blocked-by は設定せず、本文を SSoT とする。
- ## 重複調査（起票時・open/closed）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
