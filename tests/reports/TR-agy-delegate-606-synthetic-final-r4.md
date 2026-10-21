---
id: TR-agy-delegate-606-synthetic-final-r4
version: 1
condition: failure
result: FAILED
result_scope: synthetic_contract_and_related_groups
full_suite_result: "FAILED (failures=1, errors=5)"
execution_target: 038445d0fe9d6c5f73c4fd673a94ca9ce5bde089 (tree 0d76bde006040960b3c79db1e8436ef8e3034cc0)
log_ref: tests/logs/TD-agy-delegate-606-r21-full-unit.txt
---
# TR agy-delegate #606 合成契約・最終成績書

F-606-06・F-606-13の是正として、commit済みの同一対象を再測定したログに基づき本成績書を再生成した。同一未merge PR内の書き換えのためversionは1を維持する。

測定対象のcommit・treeは[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 2–3行。測定前後の状態は同ログ15–19行・237–242行、測定系列の有効性は250行で確認できる。
測定開始（started_at）はwrapper関連が`2026-10-21T23:23:29.801077+00:00`（[related-wrapper](../logs/TD-agy-delegate-606-r21-related-wrapper.txt) 4行）、全量が`2026-10-21T23:31:26.841579+00:00`（[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 4行）。Pythonは`3.12.3`、platformは`Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`（同ログ6–7行）。coverage利用確認のUTC_STARTは`2026-10-21T23:46:34.727334+00:00`（[coverage](../logs/TD-agy-delegate-606-r21-coverage.txt) 2行）。

## 現行試験契約と判定範囲

TD正本: [TD-agy-delegate-606](../designs/TD-agy-delegate-606.md)。責務別テストと同workspace順次バッチ、workspace前後差分、D0/未知stderrを合成環境で検証する。合成fixture・提供済み実測JSON正規化・静的hook契約を対象とし、実機UC・agy専用live hook・実効設定・通常run解禁を認定しない。

`result_scope`はwrapper合成契約と関連グループの記録範囲を示す。wrapper関連は135件中、merge guard以外がすべて成功しているが、グループの測定結果はFAILEDである（[related-wrapper](../logs/TD-agy-delegate-606-r21-related-wrapper.txt) 21–46行）。独立関連・追加契約確認はOK、gate/配置は環境起因のerrorsを含むFAILEDであるため、`result`もFAILEDとした。これらのグループは範囲が重なるため件数を合算しない。

`full_suite_result`は全量の実測FAILEDをそのまま記す。failures=1は本番runtime merge guardによる意図的な失敗、errors=5はCodex実行環境で一時hookを作れなかったエラーであり、環境起因でもPASSへ算入しない（[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 92–205行）。

## 測定結果

所要秒はunittestでは`Ran ... in ...s`、静的検査では`elapsed_seconds`の値を採用した。結果欄のfailures/errors/skippedはログのsummaryに記載されたものだけを転記し、記載のない項目をゼロで補完しない。静的検査には試験件数・failures/errors/skippedの集計はない。コマンドは各ログの記録どおりである。

| 測定 | 件数 | 所要秒 | 結果（ログ記載のfailures/errors/skipped） | exit | コマンド | 証跡・行番号 |
| --- | --- | --- | --- | --- | --- | --- |
| wrapper関連 | 135件 | 47.467 | FAILED (failures=1) | 1 | `TMPDIR=/dev/shm python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'` | [related-wrapper](../logs/TD-agy-delegate-606-r21-related-wrapper.txt) 1行（コマンド）、44–46行（件数・秒・結果）、56行（exit） |
| 独立関連 | 41件 | 15.278 | OK | 0 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agy_delegate_results tests.unit.test_agy_delegate_permissions tests.unit.test_agy_delegate_runner tests.unit.test_agy_delegate_artifacts tests.unit.test_agy_delegate_cli tests.unit.test_agy_delegate_gates` | [related-independent](../logs/TD-agy-delegate-606-r21-related-independent.txt) 1行（コマンド）、23–25行（件数・秒・結果）、35行（exit） |
| gate/配置 | 245件 | 410.109 | FAILED (errors=5) | 1 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agent_command_gate tests.unit.test_codex_agent_command_gate tests.unit.test_governance_sync tests.unit.test_guidance_sync tests.unit.test_ai_asset_layout tests.unit.test_silent_failure_diagnosis_layout` | [related-gate-placement](../logs/TD-agy-delegate-606-r21-related-gate-placement.txt) 1行（コマンド）、113–115行（件数・秒・結果）、125行（exit） |
| 追加契約確認 | 15件 | 3.670 | OK | 0 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agy_delegate_gates tests.unit.test_silent_failure_diagnosis_layout tests.unit.test_agy_delegate_merge_guard_contract` | [related-contract-addon](../logs/TD-agy-delegate-606-r21-related-contract-addon.txt) 1行（コマンド）、23–25行（件数・秒・結果）、35行（exit） |
| 全量 | 2397件 | 680.292 | FAILED (failures=1, errors=5) | 1 | `TMPDIR=/dev/shm python3 -m unittest discover -s tests/unit` | [full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 1行（コマンド）、203–205行（件数・秒・結果）、243行（exit） |
| merge guard単体 | 1件 | 0.001 | FAILED (failures=1) | 1 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agy_delegate_merge_guard` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 1行（コマンド）、44–46行（件数・秒・結果）、56行（exit） |
| maintainability_lint | 試験件数は対象外 | 0.508531 | violations=0 / accepted_debt=77 | 0 | `TMPDIR=/dev/shm python3 -m maintainability_lint check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 14行（コマンド）、95行（結果）、98–99行（秒・exit） |
| asset_parity | 試験件数は対象外 | 0.952990 | 49 assets checked / 0 MISSING / 18 staleness flags | 0 | `TMPDIR=/dev/shm python3 -m asset_parity check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 102行（コマンド）、158行（結果）、198–199行（秒・exit） |
| guidance_sync | 試験件数は対象外 | 0.037705 | check OK | 0 | `TMPDIR=/dev/shm python3 -m guidance_sync check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 202行（コマンド）、204行（結果）、207–208行（秒・exit） |
| git diff --check | 試験件数は対象外 | 0.003541 | 出力なし・正常終了 | 0 | `TMPDIR=/dev/shm git diff --check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 211–216行（コマンド・出力・秒・exit） |

### 環境起因エラーの根拠

全量の`test_codex_agent_command_gate`は、一時hook生成時に`.codex/hooks/`が読み取り専用で停止した。同じ原因がgate/配置にも記録されている。該当するOSErrorは[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 107・125・143・161・179行、[related-gate-placement](../logs/TD-agy-delegate-606-r21-related-gate-placement.txt) 38・56・74・92・110行で確認できる。

参考注記（ログ証跡なし・集計対象外）: 呼出元から、同じcommitの`python3 -m unittest tests.unit.test_codex_agent_command_gate`はClaude側環境でOKだったとの観測が提供された。環境起因という説明の傍証にとどめ、全量の合格認定には使用しない。

## coverage未再測定

既存`.coveragerc`を用いる前提で利用確認を試したが、どちらの経路も失敗した（[coverage](../logs/TD-agy-delegate-606-r21-coverage.txt) 35–51行）。

| 試したコマンド | 所要秒 | exit | 失敗理由 | 証跡・行番号 |
| --- | --- | --- | --- | --- |
| `TMPDIR=/dev/shm python3 -m coverage --version` | 0.015520 | 1 | No module named coverage | [coverage](../logs/TD-agy-delegate-606-r21-coverage.txt) 37–41行 |
| `TMPDIR=/dev/shm uv run --offline --with coverage coverage --version` | 0.026716 | 2 | uvキャッシュの一時ファイルを作成できず Read-only file system | [coverage](../logs/TD-agy-delegate-606-r21-coverage.txt) 43–49行 |

coverage run/report/htmlは実行されず、試験件数・coverage集計はいずれもNOT_MEASURED、生成物もない（[coverage](../logs/TD-agy-delegate-606-r21-coverage.txt) 51–61行）。coverageの数値は認定しない。

## 未達・STOP

運用状態は[.ai/agents/agy-delegate.md「現在の利用制約」](../../.ai/agents/agy-delegate.md#現在の利用制約運用状態の正本)を参照。静的検査・合成試験は通常runの停止を解除しない。

本試験で認定していない範囲: 実効resolver/decoder/merge、admin当該起動確認、Windows変換、実機version形式/model差、実機UC/画像/並列/alias/symlink/認証、agy専用roleのlive metadata/trust/dispatch、#607撤去可、default branch到達。coverage未再測定も未達事項とする。全量およびgate/配置の環境起因エラーは未解消であり、全量合格とは扱わない。

merge guard受入テスト`tests/unit/test_agy_delegate_merge_guard.py`は、本番runtimeの停止理由が残る間は意図的にFAILする。解除条件はIssue #628のAC達成であり、skip/削除/期待値反転で緑にしない（[merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 23–46行）。接尾辞に依らず全停止理由を対象とする。

検出した停止理由は7件（[merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 30行・35–41行）。

| 停止理由 | 証跡・行番号 |
| --- | --- |
| `settings_global_binding_unverified` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 35行 |
| `settings_project_binding_and_schema_unverified` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 36行 |
| `settings_shared_user_location_and_schema_unverified` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 37行 |
| `settings_admin_presence_or_precedence_unverified` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 38行 |
| `settings_layer_inventory_incomplete` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 39行 |
| `settings_permission_merge_unverified` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 40行 |
| `launch_environment_unverified` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 41行 |

過去の測定はgit履歴にある。
