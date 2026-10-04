# Jev hook レビュー是正記録

実装と別文脈のレビューで見つけた境界条件を是正した。意味精度の判定とは区別する。

| finding | 対応 | 回帰テスト |
|---|---|---|
| tool 入力・結果の秘密が状態へ残る | commit 前に本文を消去、監査は固定コードのみ | `test_api_failure_and_no_raw_content_persisted` |
| 質問キャンセルが全 session に持続 | 現在 turn に限定、新 user turn でリセット | `test_new_user_turn_resets_cancellation` |
| 質問後の説明で R3 を通過する | tool_use block 位置で履歴を切断 | `test_compaction_and_same_block_future_speech` |
| 圧縮済み履歴を完全と判定 | compact_boundary/summary は不明 | 同上 |
| Stop 重複が予算消費、旧 cache が R4 回復/編集を無視 | payload、履歴、設定、snapshot、進捗で replay 識別 | `test_stop_without_event_id_is_idempotent`, `test_same_stop_recovers_then_detects_external_edit` |
| 実 API model 版が監査へ反映されない | evaluator.last_model と質問版を保存 | evaluator/transport テストと監査コード確認 |
| 質問ツールなしなら R2 も免除 | R1 の免除と R2 調査前提を分離 | `test_unavailable_question_tool_does_not_exempt_research` |
| R4 を反復予算で迂回 | 確定前提を維持、回復 matcher を優先 | `test_budget_shadow_and_explicit_prerequisites` |
| 検証中編集を成功として認証 | Pre / Post fingerprint 一致必須 | `test_edit_during_validation_does_not_certify` |
| 最新失敗でも過去成功が残る | 検証開始時に旧成功を失効 | `test_failed_revalidation_invalidates_prior_success` |
| 公式 Bash 応答に exit_code が常在しない | stdout receipt wrapper と中断検査 | `test_official_bash_shape_requires_machine_receipt` |

実装時の通常判断として、R4 の強制前提はループ予算で解除せず不足手順の実行を通す方針を採用した。実セッションへの結線はしない。API 障害・不確実性・履歴不足だけで強制拒否しない。

追加是正: tool ID の Pre/Post 重複識別を filesystem snapshot から独立させ、古いイベントの再送で編集後コードを認証しない（`test_replayed_validation_cannot_certify_edited_code`）。同じ Pre の pending fingerprint は上書きしない。複数 Skill の pending は Skill ID で分離する。通常 CI の `tests/unit/test_jev_core.py` から全 core テストを検出する。4 プロセス同時重複処理のトランザクション整合性、条件付き/任意手順と回復操作もテストした。

## 最終検証結果（2026-10-04）

- `python -m unittest tests.unit.test_jev_core tests.unit.test_jev_evaluator tests.unit.test_jev_sdk_transport -v`: 31 件中 30 件成功、SDK 未インストールの 1 件は skip。
- SDK 0.7.2 を導入した一時 venv で同じ suite: **31 / 31 成功**。HTTP mock を使用し実 API 通信なし。
- `python3 -m maintainability_lint check`: **violations=0、accepted_debt=136**。既存 baseline の変更なし。
- 手動 stdin: shadow の Stop/Ask は `{}`、enforce R1 は Stop block、enforce R3 は PreToolUse deny。各 stdout は有効な JSON、終了コード 0。
- 既存全 unit suite は環境中断で完走結果未確認。実 Jev 精度、WSL 実機、実 Claude Code セッションは未検証。settings.json の結線・登録・実セッション有効化は実施していない。
