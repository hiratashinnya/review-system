# Issue #804「karte: 診断（diagnosis）／メモ（note）の [x, y] が dumps→parse の往復で変質し、往復のたびに引用符が増える（K-02 分割前から存在・F-799-06）」

- URL: https://github.com/hiratashinnya/review-system/issues/804
- 状態: closed（2026-11-18取得）
- 本文: 4622文字/ 94行。全文: `../raw/issues-2026-11.jsonl`
- AC: 4件（未チェック: 0）
- Issue参照: #799, #747, #745
- PR参照: #799
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 実測値 | ### 機構（コード読みで確認。起票者による実行再現は未実施） | ### 分割後の位置 | ## 再現手順 | ## 期待結果 | ## 実際結果 | ## 環境 | ## 影響 | ## root cause 仮説 | ## Scope
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - Blocked by（本文での記録。native の blocked-by relation は設定しない）: PR #799（stack L2。#747 K-02 の実装 PR）。golden の `roundtrip_exceptions` と分割後のモジュールは PR #799 に含まれ、起票時点で未 merge（draft）。本 Issue は PR #799 の merge 後に着手する（上記 AC の2番目がその golden に依存するた

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
