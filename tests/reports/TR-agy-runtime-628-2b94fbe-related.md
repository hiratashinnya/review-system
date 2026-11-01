---
id: TD-agy-runtime-628
version: 1
condition: failure
result: PASS
log_ref: tests/logs/TR-agy-runtime-628-2b94fbe-related.txt
---
# 目的

Issue #628の実runtime adapterを、現版の実測・異常fixture・5UCに基づいて完成させる。限定snapshotの通常runtime検査を実装し、本物proof reader/resolverとOS境界replayによる正常fixtureでguardのassert reasons==[]を確認する。未校正の実環境は引き続き停止し、実機5UC完了とfixtureの成功を区別する。guardをskip/削除/期待値反転しない。

# 前提と根拠

PR #627 head f09f3d099952e9da8293ae88da3749b2c276973eが下段。同一未merge PR内の是正としてTD版1を維持し、以前のTR/logを遡及変更しない。旧観測と現在を混同しないため、経緯は対応する既存TRとdocs/methods/agy-runtime-evidence-628.mdを参照する。

先行のWindows実機校正では1.4.8、親process限定AGY_CLI_DISABLE_AUTO_UPDATE=true、前後exe hash一致、元4file復元・自然終了を確認した。--print-timeoutはduration構文で30s/120sを受理し、通常JSONの必須6key・usage5key整数・turn整数を確認した。既存モデルClaude Sonnet 4.6 (Thinking)、useG1Credits=falseで秘密anchorの実読取witnessを取得した。偽corpusは不変だがwrite試行/engine拒否の証拠は未確定であり、応答文だけから拒否成功としない。

公式global schema https://antigravity.google/schemas/v1/settings.json はroot additionalProperties=true、permissionsとallow/ask/deny optional、permissionsのunknown member禁止、7種類のrule構文を定める。省略群はそのglobalの明示rule無しとして記録する。これはengine全体の実効空・既定動作・全層mergeの証明ではない。schema自体にCLI1.4.8 exact対応markerは無い。

本番Request.settingsは限定templateの検査対象のままであり、実global参加元に流用しない。確定候補はcanonical Windows exe配置からのglobal、default-cli-project.json、shared config.json。観測したhome/.local/bin/agyのleaf shimのみcanonical候補へ解決でき、未知alias/祖先symlink/未知layoutを探索しない。候補発見を層参加/schema/admin不存在の証明としない。

# 実装と試験対象

| 関数/対象 | TCと期待する検証 |
|---|---|
| settings_sources.resolve_candidate_sources | 固定3候補とadmin未知を返す。Request.settings/cache/別UUIDへfallbackしない。観測home shimは候補だけ解決し、別alias/不正配置は固定理由で停止 |
| settings_decoders.decode_global_permissions | optional省略の由来を保持し、明示ruleは空配列に射影。不正root/member/型/ruleを拒否し、正しい他群は監査へ残す |
| settings_reads.read_layer_permissions | bounded regular/no-follow読取、重複JSON/不正JSON/symlink/未読を固定理由にする。fixture decoder互換を維持し、内容/私的pathを理由へ含めない |
| settings_layers.inspect_layer_resolution | 未知adminがあっても既知extra allow/ask/deny・duplicate/typeを診断。不完全inventoryではmissing-rule全体判定を保留 |
| runner→realresolver→decoder | 人工Windows配置の異常fixtureからrunし、execute/version/subprocess起動0、fixture bytes不変、private path/rule漏洩0 |
| process.execute/version/output_contract | exact1.4.8のみ、duration秒suffix、shell非経由prompt保持、厳密JSON型検査。正常schema観測を未実測の同版拒否/ERROR/timeout効力へ転用しない |
| launch_profile.native_arguments/child_environment | version/modelともdefault-cli-projectを明示、promptを独立argvとして保持。親environmentを変えずWindows子だけauto-update抑止を継承 |
| native_policy/permission_rules/native_paths | 論理templateと実file-onlyのstrict subsetを区別。未知native rule/一覧command追加/unsafe pathを拒否。native欄は入力projectionであってOS cwd観測ではない |
| cohort_runtime/windows_probe | fake private homeの本物proof reader・real resolver・read-only OS adapterのrecord/replayで正常fixtureを通す。verify_runtime自体のmockやRequest.settingsからのproof注入は使わない |
| Windows gateway環境名 | 実helper関数に合成名8件を渡し、大文字・小文字・混在prefixを検出する。環境値・設定・CLIに接触せず、非prefix/空入力を区別する |
| Windows JSON stdin | 合成nonceだけのJSON行をBOM付き/なしUTF-8 bytesで渡し、Console.In.ReadLine→ConvertFrom-Jsonの受理差を確認する。実設定/agy0。adapterのstdin bytesとstdout decodeを分離する |
| 一時session校正producer | 実publisher/reader/normalwrapperへ接続し、未検証観測/source差異は全子0、未知global/OS再読差/直前source差は発行0。visible commitのdurability warningを呼出側へ保持する。認証fileを読まない |
| 一時session controller | 合成worker結果のみでcohort readyが関数代入pipeline外のConsoleへ到達し、nonce付き応答後だけboolを返すことを確認する。実設定/CLI0。実機ではfinally元4file復元後に本番runtimeが同proofをsnapshot差異で拒否する |
| 正規化前処理 | 準備zero-turn表示後のglobalは非permissionsの厳密JSON構造同値（次行の既知default省略だけ例外）、permissions exact、ACLowner一致を要求する。その後にbaselineを採り正式2表示全体を囲む。構造比較はobject順だけを無視し、型・array順・key/value大小文字・null/欠落を区別する |
| 既知defaultの限定省略 | 公式schemaのuseG1Credits.default=falseと実測false→欠落だけを正規化同値として認め、他の全非permissionsは厳密同値を維持。準備/正式/configの実効falseを確認し、true/文字列false/他key変更/他default省略/逆方向追加を拒否する |
| launch_identity/verified_process | known leaf shimだけを一度canonical化し、同exeを検査・起動。排他待機後/版照会後のsnapshot/source変更でmodel0、offline不正はOS helperも0 |
| settings_file_read/cohort_executable | nofollow descriptor・bounded regular・前後identity変化を検査し、原fileを変更しない |

TCはtests/unit/test_agy_delegate_settings_decoders.py、test_agy_delegate_runtime_candidates.pyと既存test_agy_delegate_settings_layers.py、process/version/measured各TC。既存TD-agy-delegate-606の分類・会話・画像・排他試験を重複定義しない。

## cohort内部保存・読取・出版のTC

cohort_*のschema/read/publication TCは、実profileを使わず偽UID homeの実fileを用いる。通常APIへproof path注入を追加しない。

| 対象 | 期待する検証 |
|---|---|
| cohort_schema/validation | protocol1の全階層unknown/missing/typeを拒否。hash/enum/true観測/account/存在を区別、UTC24h/future/期限・datetime上限overflowは固定理由 |
| cohort_paths/private_io/storage | pwd home固定、HOME/XDG不採用、全ancestor nofollow、共有755とprivate0700/ownerUIDを区別。0600regular/owner/hardlink/FIFO/64KiB、marker/欠落/改変/同bytesinode差替え/別workspace/非canonicalを拒否。全subprocess0 |
| cohort_publication | schema検証を作用前、CreateNew/fsync/readback/index atomic順とunlink commitpointを確認。not_started/pending/committedを区別し、precommit marker削除0、postcommit dirsync失敗はdurabilityfalse/warningとし虚偽rollbackしない |
| cohort_generator | 固定package top-level py/ps1全件のsorted filename→sha、下位/非source除外、引数/env manifest非採用。1MiB/regular/nofollow、各identity/集合前後不変、追加/途中変更/OS failureを固定理由で拒否・子0 |

APIはcohort_schema.validate_proof/canonical_proof_bytes、cohort_storage.read_cohort、内部専用cohort_publication.publish_calibrated_cohort。PublicationOutcomeはdata専用moduleへ分離する。temporary-session内のproof発行はaccount適用範囲確定後だけ、復元後の自然hash失効を正常な安全契約として扱う。

cohort_generator.current_generator_sha256は校正開始/発行直前で同一を確認し、通常runはOS helper前とprompt直前で一致を確認する。package編集を他authorと停止合意した試験windowで、開始HEAD/dirty scope/source closureと終端不変を記録する。

# 手順

1. source/TC/TDをローカルcommitしexact SHAを固定する。
2. 関連agy_delegate unittest、maintainability_lint、asset_parityを実施し、失敗も含めstdoutとTRを保存する。
3. 独立contextでdiffとfreezeをレビューする。主文脈が既存対象とagy_delegateのcoverageを実行する。
4. 許可先write対照・保護先不変・直接拒否未観測の限界を区分して記録し、5UCを本番wrapperで実施する。engine直接拒否logを追加の完了条件にせず、実corpus/認証を拒否試験に使わない。skip-permissions/追加購入/自動retryを行わない。

# 残余と期待結果

一般project/shared schema・全層mergeは支持対象外とし、個人アカウントの本人申告と既知admin候補/環境の不存在確認を分離する。3scopeの表示だけでremote管理policy不存在を機械断言しない。先行のcwd/selector校正と新本番W policyでの校正・実timeout顛末・5UCは別途判定し、環境/cohort変更時は再検証する。実設定の元rawは保持process memoryだけとし、固定4fileの二読・late比較・原復元・自然終了を確認する。未知時は元memoryを保持し、推測復元/強制killをしない。

5UCは影響調査・素案・外部調査・画像生成・並列。成果検証・会話/成果物対応・workspace分離・拒否/失敗も各々記録する。単体/正常fixtureのguard合格と、F01全体・実機5UC完了を区分する。全ACが揃って初めて最終完了を判断する。

# 実測（このTRの判定範囲）

- TD版1、試験commit 2b94fbe3d3640b833b42d2b484911a908f891aab、記録日2026-10-29。後続5eddf97はTD文言だけでpackage/TC不変。prompt雛形/S6評価器は対象外、argv profileはexplicit-project-json-duration-v1。
- uv Python3.13の全agy関連229件は52.129秒でPASS。fixture/異常境界の試験であり、実モデル/Windows実設定への作用0。
- package closureの開始/終端は1493aa8414594aaa7ed434eb9f0a2284a3ca8bdbf4155262158ef920282ac250で一致、開始/終端HEADも2b94fbeで一致。他authorとpackage編集停止を合意したwindowで計測した。
- 専用data /tmp/agy-singlew-guardfix.coverage、1439 statements/69 miss、表示95%。旧全量data/.coverage/HTMLは保持。coverage表はtests/logs/TR-agy-runtime-628-2b94fbe-coverage.txt。
- maintainability_lint exit0/violations0/accepted_debt77、baseline変更0。asset_parity exit0、既存age/size WARNを保持。各stdoutは同prefix-lint.txt/-asset.txt。
- 是正前229件の2 ERRORは別FAIL TR/logに保持した。guard正常fixtureの合格と実機5UC/F01完了は別で、後者は未完了。

