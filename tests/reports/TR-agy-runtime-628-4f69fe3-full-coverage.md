---
id: TD-agy-runtime-628
version: 1
condition: failure
result: FAIL
log_ref: tests/logs/TR-agy-runtime-628-4f69fe3-coverage.txt
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

TCはtests/unit/test_agy_delegate_settings_decoders.py、test_agy_delegate_runtime_candidates.pyと既存test_agy_delegate_settings_layers.py、process/version/measured各TC。既存TD-agy-delegate-606の分類・会話・画像・排他試験を重複定義しない。

# 手順

1. source/TC/TDをローカルcommitしexact SHAを固定する。
2. 関連agy_delegate unittest、maintainability_lint、asset_parityを実施し、失敗も含めstdoutとTRを保存する。
3. 独立contextでdiffとfreezeをレビューする。主文脈が既存対象とagy_delegateのcoverageを実行する。
4. mode/許可先write対照を確認して対象write試行と拒否を確定し、5UCを本番wrapperで実施する。実corpus/認証を拒否試験に使わず、skip-permissions/追加購入/自動retryを行わない。

# 残余と期待結果

admin/remote管理policy適用範囲、project/sharedの全schema、実効merge、native cwd/pathとselectorの最終束縛、実timeout顛末は未完了。既知3scopeの表示exact一致だけでadmin不存在を推論しない。環境/cohort変更時は再検証する。実設定の元rawは保持process memoryだけとし、固定4fileの二読・late比較・原復元・自然終了を確認する。未知時は元memoryを保持し、推測復元/強制killをしない。

5UCは影響調査・素案・外部調査・画像生成・並列。成果検証・会話/成果物対応・workspace分離・拒否/失敗も各々記録する。現在はpartial実装の関連試験を判定し、F01全体完了やmerge guard緑とは別に扱う。全ACが揃って初めて最終完了を判断する。

# 実測（全量coverage・失敗記録）

Codex (AI) による測定記録。実行者は主文脈、本文の作成者は別contextである。
本TRはsource commit `4f69fe3c70c58af9c34f6c17c57e1fbcdeb7be47` のTD版1をコピーし、
そのsourceを対象とした失敗を記録する。後続是正や新測定で本TR/logを上書きしない。

- 対象: 上記exact source、2026-10-28 JST、WSLのuv管理Python 3.13。
- 実行: `uv run --with coverage coverage run --source=review_system,docidx,blocker_gate,pr_merge_gate,branch_source,issue_start,agy_delegate -m unittest discover -s tests -p test_*.py`。
- 2430件、684.659秒、failures=2、テスト実行exit1。結果はFAILである。
- 失敗1: `RuntimeMergeGuardTests.test_production_runtime_has_no_unverified_stop_reasons`。
  F-628-01の未完了条件で停止理由が残っており、既存の意図的merge guardが失敗した。skip/削除/期待値反転はしていない。
- 失敗2: `RuntimeCandidateTests.test_cyclic_home_shim_returns_fixed_reason_without_launch_or_path`。
  `settings_executable_alias_unresolvable` を期待したが返却理由に含まれず、
  `executable_unavailable` と `settings_executable_unreadable` 等の停止理由が返った。
  uv Python 3.13で固定理由の期待に一致せず、F-628-29を再openした。追加の実装原因は是正側で切り分ける。
- 別実行環境のF29局所9TC PASSは `TR-agy-runtime-628-4f69fe3.md` の履歴として保持する。
  それを本全量実行の成功へ転用せず、後続sourceの合否も本TRから推定しない。

## Coverageの集計と限界

- 指定対象は既存6群（review_system/docidx/blocker_gate/pr_merge_gate/branch_source/issue_start）とagy_delegate。
- coverage reportのTOTALは6074 statements、647 miss、89%。全repositoryの全module包含を意味しない。
- agy_delegateは780 statements、34 miss、95.6%（表示表の当該module行を合計）。
- `docidx` は未importのCoverageWarningを出した。対象名の指定だけで全moduleの測定済みとは主張しない。
- `coverage html` はexit0で `htmlcov/index.html` を生成、`coverage report` もexit0だった。
  HTML/report生成成功と、前段のunittest FAILを分ける。最終reportコマンドのexit0で測定全体をPASSにしない。
- `.coverage` とHTML等の生成物はcommit対象外である。永続証拠は本TRと既存のcoverageログとする。

F-628-01・29はこの測定時点でopen。write拒否/5UC/admin/全層merge/cwd/timeout実効性・本番guard解除は未達。
本TR作成者はテスト・coverage・Windows/agy/設定操作を追加実行せず、既ログとexact TDの読取だけで記録した。
