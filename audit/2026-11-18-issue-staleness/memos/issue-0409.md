# Issue #409「AgentRun ledgerとclose gateでサブエージェント実行ライフサイクルを機械管理する」

- URL: https://github.com/hiratashinnya/review-system/issues/409
- 状態: open（2026-11-18取得）
- 本文: 8122文字/ 156行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 17件（未チェック: 17）
- Issue参照: #371, #310, #375, #331, #406, #408, #445, #368, #217, #289, #691, #783, #784, #785, #733, #683, #703
- PR参照: #408, #733
- 主見出し: ## 新しいphase・artifact・依存run | ### close gate追加条件 | ### Acceptance criteria追加 | ## 目的・背景 | ## 現状と根本原因 | ## 提案する挙動 / Scope | ## 互換性・代替案 | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 【申し送り】#691 レビュー指摘の自動仕分け・Advisory台帳（2026-10-31） | ## 【申し送り・2026-11-07】#691 triager run/正本artifactの接続点
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- 現状は、実行全体について `agent_id` / `target_key`、phase、期待成果物、handoff、heartbeat / last_activity、次回確認時刻、状態遷移を1つの durable な機械可読レコードとして管理していない。transport の wait timeout と worker failure を区別する状態遷移もなく、完了通知と handoff・成果物検証・未解消 finding の確認を結合した close
- - 現在の Issue #406 / PR #408 による資産分離修正そのもの。
- - **実装時の扱い**：双方の最新仕様・機械ゲート・テストを突き合わせ、既存契約を覆す変更は理由とオーナー承認を記録する。正式なGitHub relation/blocked-by設定は、本追記とは別に確定する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
