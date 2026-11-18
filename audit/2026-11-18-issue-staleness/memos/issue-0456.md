# Issue #456「fix(codex): レートリミット解除時刻の推定が参考情報の枠に引きずられ、画面文字列読み取りへのフォールバックが発動しない」

- URL: https://github.com/hiratashinnya/review-system/issues/456
- 状態: closed（2026-11-18取得）
- 本文: 3521文字/ 68行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #455, #195
- PR参照: #455
- 主見出し: ## 背景・経緯 | ## 現状と根拠 | ### 挙動の説明（一般的な用語で） | ### 参考: PR #455 のレビューコメント | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- このとき現在の実装（`codex-rate-limit-query.py` の `pick_binding_window`）には、「原因の枠が見つからない場合は、代わりに、今後解除予定の枠の中で一番使用率が高いものを参考情報として返す」という仕組みがある。これは元々「制限中ではないが参考までに知りたい」時のための機能だが、「制限中である」ときにもこの仕組みが動いてしまう。
- - `tests/unit/test_codex_rate_limit_api.py` の `StopHookReachedWithoutResetEpochFallsBackTests`（F-455-3）を、実バナー文言を投入して画面文字列読み取りの経路まで到達することを検証できるよう強化する（現状は「参考として時刻を返さない」ところまでしか確認できていない）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
