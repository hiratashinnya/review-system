---
id: TD-agy-runtime-628
version: 1
condition: failure
result: PASS
log_ref: tests/logs/TR-agy-runtime-628-d4a0278-native.txt
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

TCはtests/unit/test_agy_delegate_settings_decoders.py、test_agy_delegate_runtime_candidates.pyと既存test_agy_delegate_settings_layers.py、process/version/measured各TC。既存TD-agy-delegate-606の分類・会話・画像・排他試験を重複定義しない。

# 手順

1. source/TC/TDをローカルcommitしexact SHAを固定する。
2. 関連agy_delegate unittest、maintainability_lint、asset_parityを実施し、失敗も含めstdoutとTRを保存する。
3. 独立contextでdiffとfreezeをレビューする。主文脈が既存対象とagy_delegateのcoverageを実行する。
4. mode/許可先write対照を確認して対象write試行と拒否を確定し、5UCを本番wrapperで実施する。実corpus/認証を拒否試験に使わず、skip-permissions/追加購入/自動retryを行わない。

# 残余と期待結果

admin/remote管理policy適用範囲、project/sharedの全schema、実効merge、native cwd/pathとselectorの最終束縛、実timeout顛末は未完了。既知3scopeの表示exact一致だけでadmin不存在を推論しない。環境/cohort変更時は再検証する。実設定の元rawは保持process memoryだけとし、固定4fileの二読・late比較・原復元・自然終了を確認する。未知時は元memoryを保持し、推測復元/強制killをしない。

5UCは影響調査・素案・外部調査・画像生成・並列。成果検証・会話/成果物対応・workspace分離・拒否/失敗も各々記録する。現在はpartial実装の関連試験を判定し、F01全体完了やmerge guard緑とは別に扱う。全ACが揃って初めて最終完了を判断する。

# 実測（native launch profileのみ）

- TD版1 / native source d4a027865a004722e673956c271a3f675d8fb5fe / 試験checkout c3bad31ade4a906fef334d20567c351ff68a021a / prompt雛形・基準content_hash N/A / 2026-10-28 JST / uv Python3.13.14。
- 明示launch_profile/process/version_contract/runnerの21TC、12.182秒、全成功。peer cohort TCは含めず、実機WSL→Windows継承/cwdの成功証明とは区別する。
- lint exit0、violations0、accepted_debt77、baseline変更0。tests/logs/TR-agy-runtime-628-d4a0278-lint.txt。AI資産差分0のためasset_parityはf9dba37時点のMISSING0を参照。
- 親environment不変、固定selector・native argv prompt独立、子限定updateenvを検証。未確定cohort/5UC・既mergeguard FAILを完了扱いしない。
