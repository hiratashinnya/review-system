# Issue #302「Codex rate-limit watcherの固定epoch期限切れでunit testが失敗する」

- URL: https://github.com/hiratashinnya/review-system/issues/302
- 状態: closed（2026-11-18取得）
- 本文: 2640文字/ 88行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #301, #295
- PR参照: #301
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 再現手順 | ## 期待結果 | ## 実際結果 | ## 環境 | ## 影響 | ## Root cause 仮説 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- テストが実行時刻を注入・固定せず、固定 epoch `1783767886` と現在時刻の相対関係に依存しているため、時間窓を過ぎると本来正常系として検証したい入力が `FALLBACK` へ分岐する。
- - [ ] fixed epoch と現在時刻の偶発的な相対関係に依存する test data が残っていない。
- - Blocked by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
