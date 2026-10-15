---
id: TR-agy-delegate-606-synthetic-final-r4
version: 1
condition: failure
result: PASS
result_scope: synthetic_contract_only
full_suite_result: EXPECTED_MERGE_GUARD_FAILURE
execution_target: 1940b14 + uncommitted round-6 remediation
log_ref: tests/logs/TD-agy-delegate-606-r6-final-full-unit.txt
---
# TR agy-delegate #606 r4 合成契約・最終成績書

現行実行対象: commit 1940b14 ＋本是正の未commit作業ツリー差分。ユーザーのGit操作禁止を優先したcommit-before-test例外。Linux / Python3 / 2026-10-13、prompt版・基準content_hashは該当なし。同一PRのversion 1を維持する。最終状態の成績書は本書のみ。PASSは合成fixture・提供済み実測JSON正規化・静的hook契約に限定し、実機UC・agy専用live hook・実効設定・通常run解禁を認定しない。

## 現行試験契約

TD正本: [TD-agy-delegate-606](../designs/TD-agy-delegate-606.md)。責務別テストと同workspace順次バッチ、workspace前後差分、D0/未知stderrを合成環境で検証する。全量のmerge guardは本番runtimeのreasonsが1つでもあれば意図的にFAILする。合成契約PASSと全量FAILの範囲を区別する。

## r4 実測履歴（commit 41be85d＋当時差分、元の成否を保持）

- wrapper関連: 63件 / 12.856秒 / PASS。
- 独立関連: 40件 / 13.619秒 / PASS。
- Claude/Codex gate・governance・配置全体: 183件 / 380.007秒 / PASS。
- python3 -m unittest discover -s tests/unit: 2003件 / 492.492秒 / OK (skipped=9)、exit 0。当時の証跡: tests/logs/TD-agy-delegate-606-r4-unit.txt。
- maintainability_lint: violations=0、accepted_debt=104、exit 0、baseline不変。
- asset_parity / guidance_sync / git diff --check: exit 0。既存stale警告保持。
- CLAUDE.md SHA256開始/終了一致: 0311068ebdb81d098410f82db44886e0b2c108b51d87efc4f7439da093909e9b。
- 未定義flag mutation: --skip-inspection仮追加・値消費で1件FAIL/exit1、finally bytes復元後1件PASS。独立レビューでも復元後PASS。

## coverage・初回失敗と回復

初回は依存取得時のsandbox DNS失敗でexit2、計測未開始。失敗記録は tests/logs/TD-agy-delegate-606-r4-coverage-network-failed.txt に保持。限定escalation自動承認後、uv run --with coverage経路で再実行した。

coverage初回discover: 1990件 / 401.807秒 / FAILED (errors=3, skipped=9)、exit1（既存bare importの発見パス問題）。失敗3モジュールをPYTHONPATH=tests/unitでappend再実行: 16件 / 0.108秒 / OK、全3コマンドexit0。実テストは1987＋16=2003件、9件skip。TOTAL 4542    566    88%。
計測対象は .coveragerc の review_system / docidx / blocker_gate / pr_merge_gate / branch_source / issue_start。wrapper自身のcoverageではない。HTMLは htmlcov/index.html（未追跡）。発見パス失敗ログ: tests/logs/TD-agy-delegate-606-r4-coverage-discovery-failed.txt、回復とHTML/reportログ: tests/logs/TD-agy-delegate-606-r4-coverage-recovery.txt。既存bare importコードは対象外として変更せず、失敗3モジュールだけ環境のimportパスを補って再実行した。計測全体を一括PASSと偽装しない。

coverage は `Module docidx was never imported` 警告を残した。上記88%はreportに載った計測範囲であり、docidxの計測完了やwrapper自身のカバレッジを示さない。

## 未達・STOP

運用状態は .ai/agents/agy-delegate.md の「現在の利用制約」を参照。本試験で認定していない範囲: 実効resolver/decoder/merge、admin当該起動確認、Windows変換、実機version形式/model差、実機UC/画像/並列/alias/symlink/認証、agy専用roleのlive metadata/trust/dispatch、#607撤去可、default branch到達は未達。(1)(14)(15)は対象外。

PR #627 の merge guard 受入テスト `tests/unit/test_agy_delegate_merge_guard.py` を追加。本番 resolver が返す設定層・権限merge・起動環境の未確認停止理由により、Issue #628 の AC 未達の間は意図的に赤となる。上記 r4 の PASS は追加前の記録であり、merge guard の合格や PR の AC 達成を示さない。解除条件は #628 の AC、skip/削除/期待値反転で緑にしない。追加後とr6の実測は本書末尾に収録する。同一未merge PR 内の追記のため version 1 を維持する。

## r5 merge guard 追加後の実測履歴（元の成否を保持）

r5は合成設定とRequestを一時領域に作り、本番runtime.verify_runtimeを差替えなしで検査した。当時のguardはcolon前の理由名が_unverifiedで終わるものだけを対象とし、停止理由6件を検出した。接尾辞依存は本r6で全reasons対象へ是正したため、以下は当時の計測結果である。

ガード単体: python3 -m unittest tests.unit.test_agy_delegate_merge_guard、1件 / 0.001秒 / FAILED (failures=1)、exit1。失敗理由6件はsettings_global_binding_unverified、settings_project_binding_and_schema_unverified、settings_shared_user_location_and_schema_unverified、settings_admin_presence_or_precedence_unverified、settings_permission_merge_unverified、launch_environment_unverified。指定のIssue #628未完了による意図的なFAILメッセージを確認した。

全量unittestはuv run --offline --with coverage coverage run -m unittest discover -s tests/unitによるcoverage同時計測で、2004件 / 422.831秒 / FAILED (failures=1, skipped=9)、errors=0、exit1。成功1994件・既存skip9件・失敗はmerge guard1件のみ。環境はLinux / uvキャッシュのPython3.13 / 2026-10-13（単体は既定python3）。証跡: [r5全量ログ](../logs/TD-agy-delegate-606-r5-full-unit.txt)。

coverage html/reportは両方exit0、TOTAL 4542 statements / 566 miss / 88%、HTMLはhtmlcov/index.html（未追跡）。.coveragercの範囲の数字でありagy_delegate自身のcoverageではない。Module docidx was never imported警告を保持。証跡: [r5 coverage summary](../logs/TD-agy-delegate-606-r5-coverage-summary.txt)。

新規ガード追加後の静的検証はmaintainability_lint exit0 / violations=0 / accepted_debt=104 / baseline不変、asset_parity exit0 / 41 assets / 0 MISSING / 既存staleness29件、guidance_sync exit0 / check OK、diff --check exit0。証跡: [r5 lint](../logs/TD-agy-delegate-606-r5-maintainability_lint.txt)、[r5 parity](../logs/TD-agy-delegate-606-r5-asset_parity.txt)、[r5 sync](../logs/TD-agy-delegate-606-r5-guidance_sync.txt)。

当時の独立read-onlyレビューはfindingなし。本番resolver・テスト1件・指定メッセージ・実機設定/agy非使用・TD/TR追記を確認した。commit/push/branch操作なし、CLAUDE.md変更なし、既存作業ツリー変更を保持。commit-before-testと全件PASS条件に対し、オーナーのcommit禁止と意図的guard FAIL指示を優先した。追跡外の当時レポートにあった測定情報を本節と上記追跡ログへ収録した。

## r6 現行実測（commit 1940b14＋本是正差分）

wrapper関連は71件 / 35.907秒 / FAILED (failures=1)、exit1。唯一の失敗は本番runtimeの全停止理由を拒否するmerge guardであり、残る70件の合成契約はPASS。証跡は [r6関連ログ](../logs/TD-agy-delegate-606-r6-related-unit.txt)。接尾辞なし停止理由と固定理由除去後のinventory不足に対するguard否定検査はPASS。gate/配置/guard契約の追加確認は12件 / 2.017秒 / PASS。最終plain全量の確定結果は以下に収録する。

maintainability_lint: violations=0、accepted_debt=104、baseline不変。asset_parity/guidance_sync/diff --check: exit0。実機設定読取・生agy起動・通常run解禁は行っていない。同一未merge PRでversion 1を維持。

### r6 初回全量・coverage（開始後追加した2件は別測定）

初回plain全量は2009件 / 652.802秒 / FAILED (failures=1, skipped=10)、exit1。唯一の失敗はmerge guard。証跡は [初回全量ログ](../logs/TD-agy-delegate-606-r6-full-initial.txt)。追加guard契約2件を含む最終plain全量とは別の測定として保持する。

coverage初回は2009件 / 637.928秒 / FAILED (failures=1, skipped=10)、exit1。開始後に追加したguard契約2件をcoverage --appendで実行し2件 / 0.004秒 / PASS、exit0。HTML/report生成はexit0、TOTAL 4542 / Miss 566 / 88%。証跡は [coverage初回](../logs/TD-agy-delegate-606-r6-coverage-initial.txt)、[append・HTML・report](../logs/TD-agy-delegate-606-r6-coverage-summary.txt)。初回2009件＋append2件の計測であり、全量一括PASSとは認定しない。旧測定skipped9に対し今回はskipped10を観測した。

計測範囲は既存 .coveragerc に従い、agy_delegateのcoverageやdocidxの計測完了を示さない。Module docidx was never imported警告は残る。HTMLはhtmlcov/index.html（未追跡）。ログに含まれるreverted 1 commit(s)は既存テストの一時fixture内操作の出力であり、本作業対象でのcommit/push/branch操作を示さない。

### r6 最終plain全量（追加guard契約2件を含む最終コード）

python3 -m unittest discover -s tests/unit は2011件 / 655.868秒 / FAILED (failures=1, skipped=10)、errors=0、exit1。成功2000件、skip10件、FAIL1件。唯一の失敗は本番runtime merge guardであり、合成契約PASSとfull_suite_result EXPECTED_MERGE_GUARD_FAILUREを区別する。証跡は [最終全量ログ](../logs/TD-agy-delegate-606-r6-final-full-unit.txt)。本番runtimeの停止理由7件にはsettings_layer_inventory_incompleteを含み、接尾辞に依らず1件以上を拒否した。

実行対象はfrontmatterのcommit 1940b14＋本是正差分。初回plain2009件とcoverage2009件＋append2件は別測定として前節に保持した。旧r4のPASS・coverage初回errors3等の履歴成否は改変していない。
