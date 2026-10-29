---
id: TD-agy-runtime-628
version: 1
condition: failure
---
# 目的

Issue #628の実runtime adapterを、現版の実測・異常fixture・5UCに基づいて完成させる。現在は確定した縦sliceを実装した段階であり、admin/全層合成/起動環境/timeout実効性/5UCが未完了のため本番guardは残す。既存の意図的失敗テストをskip/削除/期待値反転しない。

# 前提と根拠

PR #627 head f09f3d099952e9da8293ae88da3749b2c276973eが下段。同一未merge PR内の是正としてTD版1を維持し、以前のTR/logを遡及変更しない。旧観測と現在を混同しないため、経緯は対応する既存TRとdocs/methods/agy-runtime-evidence-628.mdを参照する。

現在の新snapshotに基づくWindows実機観測では1.4.8、親process限定AGY_CLI_DISABLE_AUTO_UPDATE=true、前後exe hash一致、元4file復元・自然終了を確認した。--print-timeoutはduration構文で30s/120sを受理し、通常JSONの必須6key・usage5key整数・turn整数を確認した。既存モデルClaude Sonnet 4.6 (Thinking)、useG1Credits=falseで秘密anchorの実読取witnessを取得した。偽corpusは不変だがwrite試行/engine拒否の証拠は未確定であり、応答文だけから拒否成功としない。

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
4. mode/許可先write対照を確認して対象write試行と拒否を確定し、5UCを本番wrapperで実施する。実corpus/認証を拒否試験に使わず、skip-permissions/追加購入/自動retryを行わない。

# 残余と期待結果

admin/remote管理policy適用範囲、project/sharedの全schema、実効merge、native cwd/pathとselectorの最終束縛、実timeout顛末は未完了。既知3scopeの表示exact一致だけでadmin不存在を推論しない。環境/cohort変更時は再検証する。実設定の元rawは保持process memoryだけとし、固定4fileの二読・late比較・原復元・自然終了を確認する。未知時は元memoryを保持し、推測復元/強制killをしない。

5UCは影響調査・素案・外部調査・画像生成・並列。成果検証・会話/成果物対応・workspace分離・拒否/失敗も各々記録する。現在はpartial実装の関連試験を判定し、F01全体完了やmerge guard緑とは別に扱う。全ACが揃って初めて最終完了を判断する。
