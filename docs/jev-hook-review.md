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

## PR571 の追加是正（2026-10-05）

| finding | 根因と修正 | 回帰テスト |
|---|---|---|
| F-572-001: 同一 Stop が条件パスの作成・削除を反映しない | replay key が watch の fingerprint だけを参照し、watch 外の `when.path_exists` を見なかった。条件パスの現在の存在値も key に含める | `test_same_stop_tracks_unwatched_condition_in_both_directions` |
| F-572-002: 後から開始した検証が失敗しても古い成功が復活する | 開始時の失効だけでは重なる検証の完了順を制御できなかった。Skill・手順ごとに最新開始の tool ID を保持し、その試行の成功だけを認証する。失敗結果でも pending を消費する | `test_later_failure_wins_over_older_success_and_recovers`, `test_late_older_failure_preserves_newer_success`, `test_duplicate_older_events_do_not_replace_latest_attempt` |

最新開始は SQLite トランザクション内で受信した PreToolUse の順とする。重複 Pre/Post は既存の replay 識別で除外し、古い成功で最新の失敗・実行中状態を上書きしない。遅れて届いた古い失敗でも最新成功を取り消さない。新たな成功検証では Stop と納品操作の両ゲートが回復する。

- 修正前: 追加4テストを実行し、7 subtest の失敗を再現。修正後: 追加4テスト成功。
- `/tmp/jev-sdk-venv/bin/python -m unittest tests.unit.test_jev_core tests.unit.test_jev_evaluator tests.unit.test_jev_sdk_transport -v`: **35 / 35 成功、skip なし**。SDK 0.7.2 と HTTP mock を使用し、実 API 通信なし。
- `python3 -m maintainability_lint check`: **violations=0、accepted_debt=136**。baseline の変更なし。変更 Python module はすべて100物理行以内。
- ローカル全 unit suite は未実行。是正前 head `3159df2235bf7375940b0d5766f2ae116bbab006` の GitHub Actions run `37201099510` は feedback-ledger / typecheck / unittest の3 checks が成功し、unittest job の unit / time / maintainability step も成功した。是正後 head の CI 結果は公開後に別途確認する。

## F-572-003: 検査契約変更による証拠の失効（2026-10-05）

根因: progress と pending は対象ファイルの fingerprint だけを保存し、検査コマンドや watch 定義を成功証拠に結び付けていなかった。同じ step ID の evidence を `test` から `test-v2` へ変えても古い成功を認め、存在しないファイルを watch に追加した場合も対象 fingerprint が変わらず、変更前の pending を認証できた。

修正: step 定義全体を正規化 JSON からハッシュ化し、対象 fingerprint と組にして progress / pending に保持する。現在の契約と一致しない成功は失効し、変更前の pending は現在の契約の成功証拠にならない。契約ハッシュは手順ごとに独立し、無関係な手順の変更で他の成功を失効させない。契約ハッシュがない旧状態も再検証を要求する。新契約に一致する Pre / Post の成功で Stop と納品操作を回復する。

- 回帰テスト: `test_contract_change_invalidates_success_and_new_validation_recovers`, `test_contract_change_rejects_old_pending_result_and_recovers` は evidence / watch の両変更を確認。`test_unrelated_step_change_preserves_success` は他手順への影響を確認。
- 修正前: 追加3テストで4 subtest の失敗を再現。修正後: SDK 0.7.2 導入済み一時 venv の指定3 suite は **38 / 38 成功、skip なし**。HTTP mock を使用し実 API 通信なし。
- `python3 -m maintainability_lint check`: **violations=0、accepted_debt=136**。baseline の変更なし。変更 Python module はすべて100物理行以内。

## F-572-004: README の Issue 状態更新（2026-10-05）

根因: 当初 GitHub API の403で作成できなかった説明が、Issue #572 作成後も README に残っていた。現在の対応 Issue のリンクと、ローカルの Issue 本文ファイルをコミットに含めない方針へ更新した。コード変更はなく、追加テストは不要と判断した。`git diff --check` と maintainability lint（violations=0、accepted_debt=136）を確認し、既存の38件成功のコード検証結果は保持する。
