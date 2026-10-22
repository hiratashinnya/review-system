---
id: TR-agy-delegate-606-synthetic-final-r4
version: 1
condition: failure
result: FAILED
result_scope: synthetic_contract_and_related_groups
full_suite_result: "Codex: FAILED (failures=1, errors=5); 主文脈: FAILED (failures=1)"
execution_target: 038445d0fe9d6c5f73c4fd673a94ca9ce5bde089 (tree 0d76bde006040960b3c79db1e8436ef8e3034cc0)
log_ref: tests/logs/TD-agy-delegate-606-r21-full-unit.txt
---
# TR agy-delegate #606 合成契約・最終成績書

F-606-06・F-606-13の是正として、commit済みの対象を再測定したログに基づき本成績書を再生成した。同一未merge PR内の書き換えのためversionは1を維持する。

wrapper関連・独立関連・gate/配置・追加契約確認・Codex環境の全量・静的検査・merge guard単体の測定対象は`038445d`（frontmatterの`execution_target`）であり、commit・treeは[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 2–3行。測定前後の状態は同ログ15–19行・237–242行、測定系列の有効性は250行で確認できる。
coverageの測定対象は`a686436`であり、commit・treeは[coverage-measured](../logs/TD-agy-delegate-606-r21-coverage-measured.txt) 3行に記録されている。主文脈の全量の測定対象commit `a686436`は、主文脈の測定時の作業記録による（[r21-fullsuite-main-env](../logs/TD-agy-delegate-606-r21-fullsuite-main-env.txt)ログには記録なし）。

以下の差分の根拠は、ログの証跡ではなくgitコマンドの出力に基づく。`038445d`→`a686436`の差分は9ファイル（`tests/logs/`の8ファイルと`tests/reports/`の1ファイル）のみで、`agy_delegate/`の実装および`tests/unit/`の関連試験に差はない。実行コマンドと出力は以下のとおり。

```text
TMPDIR=/dev/shm git diff --name-only 038445d a686436
tests/logs/TD-agy-delegate-606-r21-coverage.txt
tests/logs/TD-agy-delegate-606-r21-full-unit.txt
tests/logs/TD-agy-delegate-606-r21-merge-guard.txt
tests/logs/TD-agy-delegate-606-r21-related-contract-addon.txt
tests/logs/TD-agy-delegate-606-r21-related-gate-placement.txt
tests/logs/TD-agy-delegate-606-r21-related-independent.txt
tests/logs/TD-agy-delegate-606-r21-related-wrapper.txt
tests/logs/TD-agy-delegate-606-r21-static-checks.txt
tests/reports/TR-agy-delegate-606-synthetic-final-r4.md
```

`a686436`→`06bfc2e`についても、差分は`tests/logs/`の3ファイルと`tests/reports/`の1ファイルのみで、`agy_delegate/`・`tests/unit/`を含まない。以下は成績書を含むcommit（`06bfc2e`）時点の出力であり、今回の文書修正後のcommitに対する差分ではない。

```text
TMPDIR=/dev/shm git diff --name-only a686436 06bfc2e
tests/logs/TD-agy-delegate-606-r21-coverage-measured.txt
tests/logs/TD-agy-delegate-606-r21-coverage-testrun.txt
tests/logs/TD-agy-delegate-606-r21-fullsuite-main-env.txt
tests/reports/TR-agy-delegate-606-synthetic-final-r4.md
```

対象tree IDは、次のgit rev-parseの出力による。ログ上の記録は、`038445d`が[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 3行、`a686436`が[coverage-measured](../logs/TD-agy-delegate-606-r21-coverage-measured.txt) 3行である。

```text
TMPDIR=/dev/shm git rev-parse 038445d^{tree}
0d76bde006040960b3c79db1e8436ef8e3034cc0
TMPDIR=/dev/shm git rev-parse a686436^{tree}
c96fa86cfc16e9a96324b09b8173330e5bff3697
```

Codex環境の測定開始（started_at）はwrapper関連が`2026-10-21T23:23:29.801077+00:00`（[related-wrapper](../logs/TD-agy-delegate-606-r21-related-wrapper.txt) 4行）、全量が`2026-10-21T23:31:26.841579+00:00`（[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 4行）。Pythonは`3.12.3`、platformは`Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`（同ログ6–7行）。coverage利用確認のUTC_STARTは`2026-10-21T23:46:34.727334+00:00`（[coverage](../logs/TD-agy-delegate-606-r21-coverage.txt) 2行）。

## 現行試験契約と判定範囲

TD正本: [TD-agy-delegate-606](../designs/TD-agy-delegate-606.md)。責務別テストと同workspace順次バッチ、workspace前後差分、D0/未知stderrを合成環境で検証する。合成fixture・提供済み実測JSON正規化・静的hook契約を対象とし、実機UC・agy専用live hook・実効設定・通常run解禁を認定しない。

`result_scope`はwrapper合成契約と関連グループの記録範囲を示す。wrapper関連は135件中、merge guard以外がすべて成功しているが、グループの測定結果はFAILEDである（[related-wrapper](../logs/TD-agy-delegate-606-r21-related-wrapper.txt) 21–46行）。独立関連・追加契約確認はOK、gate/配置は環境起因のerrorsを含むFAILEDであるため、`result`もFAILEDとした。これらのグループは範囲が重なるため件数を合算しない。

`full_suite_result`は両環境の全量の実測FAILEDを併記する。Codex環境はfailures=1・errors=5で、errorsは一時hookを作れなかった環境起因のエラーであり、PASSへ算入しない（[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 92–205行）。主文脈の環境はfailures=1・unittestのerrorsなし（[fullsuite-main-env](../logs/TD-agy-delegate-606-r21-fullsuite-main-env.txt) 93–95行）。両環境のfailures=1は本番runtime merge guard（#628）による意図的な失敗である（[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 182–205行、[fullsuite-main-env](../logs/TD-agy-delegate-606-r21-fullsuite-main-env.txt) 72–95行）。

## 測定結果

所要秒はunittestでは`Ran ... in ...s`、静的検査では`elapsed_seconds`の値を採用した。結果欄のfailures/errors/skippedはログのsummaryに記載されたものだけを転記し、記載のない項目をゼロで補完しない。静的検査には試験件数・failures/errors/skippedの集計はない。コマンドは各ログの記録どおりである。

| 測定 | 件数 | 所要秒 | 結果（ログ記載のfailures/errors/skipped） | exit | コマンド | 証跡・行番号 |
| --- | --- | --- | --- | --- | --- | --- |
| wrapper関連 | 135件 | 47.467 | FAILED (failures=1) | 1 | `TMPDIR=/dev/shm python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'` | [related-wrapper](../logs/TD-agy-delegate-606-r21-related-wrapper.txt) 1行（コマンド）、44–46行（件数・秒・結果）、56行（exit） |
| 独立関連 | 41件 | 15.278 | OK | 0 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agy_delegate_results tests.unit.test_agy_delegate_permissions tests.unit.test_agy_delegate_runner tests.unit.test_agy_delegate_artifacts tests.unit.test_agy_delegate_cli tests.unit.test_agy_delegate_gates` | [related-independent](../logs/TD-agy-delegate-606-r21-related-independent.txt) 1行（コマンド）、23–25行（件数・秒・結果）、35行（exit） |
| gate/配置 | 245件 | 410.109 | FAILED (errors=5) | 1 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agent_command_gate tests.unit.test_codex_agent_command_gate tests.unit.test_governance_sync tests.unit.test_guidance_sync tests.unit.test_ai_asset_layout tests.unit.test_silent_failure_diagnosis_layout` | [related-gate-placement](../logs/TD-agy-delegate-606-r21-related-gate-placement.txt) 1行（コマンド）、113–115行（件数・秒・結果）、125行（exit） |
| 追加契約確認 | 15件 | 3.670 | OK | 0 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agy_delegate_gates tests.unit.test_silent_failure_diagnosis_layout tests.unit.test_agy_delegate_merge_guard_contract` | [related-contract-addon](../logs/TD-agy-delegate-606-r21-related-contract-addon.txt) 1行（コマンド）、23–25行（件数・秒・結果）、35行（exit） |
| 全量（Codex環境） | 2397件 | 680.292 | FAILED (failures=1, errors=5) | 1 | `TMPDIR=/dev/shm python3 -m unittest discover -s tests/unit` | [full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 1行（コマンド）、203–205行（件数・秒・結果）、243行（exit） |
| 全量（主文脈の環境） | 2397件 | 659.482 | FAILED (failures=1) | 記録なし | ログにコマンド記録なし | [fullsuite-main-env](../logs/TD-agy-delegate-606-r21-fullsuite-main-env.txt) 93行（件数・秒）、95行（結果）。測定対象commit `a686436`は主文脈の測定時の作業記録による（r21-fullsuite-main-envログには記録なし） |
| merge guard単体 | 1件 | 0.001 | FAILED (failures=1) | 1 | `TMPDIR=/dev/shm python3 -m unittest tests.unit.test_agy_delegate_merge_guard` | [merge-guard](../logs/TD-agy-delegate-606-r21-merge-guard.txt) 1行（コマンド）、44–46行（件数・秒・結果）、56行（exit） |
| maintainability_lint | 試験件数は対象外 | 0.508531 | violations=0 / accepted_debt=77 | 0 | `TMPDIR=/dev/shm python3 -m maintainability_lint check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 14行（コマンド）、95行（結果）、98–99行（秒・exit） |
| asset_parity | 試験件数は対象外 | 0.952990 | 49 assets checked / 0 MISSING / 18 staleness flags | 0 | `TMPDIR=/dev/shm python3 -m asset_parity check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 102行（コマンド）、158行（結果）、198–199行（秒・exit） |
| guidance_sync | 試験件数は対象外 | 0.037705 | check OK | 0 | `TMPDIR=/dev/shm python3 -m guidance_sync check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 202行（コマンド）、204行（結果）、207–208行（秒・exit） |
| git diff --check | 試験件数は対象外 | 0.003541 | 出力なし・正常終了 | 0 | `TMPDIR=/dev/shm git diff --check` | [static-checks](../logs/TD-agy-delegate-606-r21-static-checks.txt) 211–216行（コマンド・出力・秒・exit） |

### 環境起因エラーの根拠

Codex環境の全量の`test_codex_agent_command_gate`は、一時hook生成時に`.codex/hooks/`が読み取り専用で停止した。同じ原因がgate/配置にも記録されている。該当するOSErrorは[full-unit](../logs/TD-agy-delegate-606-r21-full-unit.txt) 107・125・143・161・179行、[related-gate-placement](../logs/TD-agy-delegate-606-r21-related-gate-placement.txt) 38・56・74・92・110行で確認できる。

参考注記（ログ証跡なし・集計対象外）: 呼出元から、`038445d`の`python3 -m unittest tests.unit.test_codex_agent_command_gate`はClaude側環境でOKだったとの観測が提供された。環境起因という説明の傍証にとどめ、全量の合格認定には使用しない。

## coverage測定結果

Codex環境ではcoverageモジュールがなく、uv経由も読み取り専用のキャッシュで失敗して測定できなかった履歴を残す（[coverage](../logs/TD-agy-delegate-606-r21-coverage.txt) 37–52行）。その後、主文脈の環境で既存`.coveragerc`を用いて測定した。

coverageは`Coverage.py, version 7.16.2 with C extension`（[coverage-measured](../logs/TD-agy-delegate-606-r21-coverage-measured.txt) 2行）、測定commitは`a686436f5557b7d25e1b908c93af61f6d79dffbc`（tree `c96fa86cfc16e9a96324b09b8173330e5bff3697`、同ログ3行）。実行命令はログの記載どおり以下である（同ログ1・4行）。`<tmp>`はログ中の表記を保持している。

```text
COVERAGE_FILE=<tmp>/cov.dat coverage run --rcfile=.coveragerc -m unittest discover -s tests/unit -p 'test_*.py'
COVERAGE_FILE=<tmp>/cov.dat coverage report --rcfile=.coveragerc
```

| 測定 | Stmts | Miss | Cover | 証跡・行番号 |
| --- | --- | --- | --- | --- |
| TOTAL | 5294 | 613 | 88% | [coverage-measured](../logs/TD-agy-delegate-606-r21-coverage-measured.txt) 116行（全行出力は5–116行） |

coverage付き全量は2397件・700.519秒で`FAILED (failures=1)`（[coverage-testrun](../logs/TD-agy-delegate-606-r21-coverage-testrun.txt) 93・95行）。この失敗も意図的なmerge guard（#628）によるもの（同ログ72–90行）。`CoverageWarning: Module docidx was never imported. (module-not-imported)`が記録されている（同ログ96–97行）。coverage-measuredの3行はcoverageの測定commit・treeの記録であり、coverage-testrunログ自体には測定commit・treeの記録がない。coverage付き全量の測定対象commitはcoverage-testrunログ単独からは確認できない。主文脈のcoverageなし全量の測定対象commit `a686436`は、主文脈の測定時の作業記録による（r21-fullsuite-main-envログには記録なし）。日時や、ログに記録されていない実行条件は補完しない。

再現できなかった旧値（TOTAL 4542 / 566 / 88%）は、今回の測定と文数が異なる。

## 未達・STOP

運用状態は[.ai/agents/agy-delegate.md「現在の利用制約」](../../.ai/agents/agy-delegate.md#現在の利用制約運用状態の正本)を参照。静的検査・合成試験は通常runの停止を解除しない。

本試験で認定していない範囲: 実効resolver/decoder/merge、admin当該起動確認、Windows変換、実機version形式/model差、実機UC/画像/並列/alias/symlink/認証、agy専用roleのlive metadata/trust/dispatch、#607撤去可、default branch到達。Codex環境の全量およびgate/配置の環境起因エラーは未解消であり、主文脈の全量にも意図的なmerge guardの失敗が残るため、全量合格とは扱わない。

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
