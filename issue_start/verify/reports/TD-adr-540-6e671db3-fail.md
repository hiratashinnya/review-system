---
id: TD-adr-540
version: 1
condition: normal
result: FAIL
log_ref: issue_start/verify/logs/TD-adr-540-6e671db3-unit.txt
---
# 目的

道具別ADRのスキーマ、追跡状態、永続化、参照、通知、棚卸し、Issue起票を検証する。

# 前提

標準ライブラリ、git、GitHub境界のfake runner。一時repoと2つのADR rootを使用。TCは tests/unit/test_adr.py。

# 手順と期待結果

1. alternatives欠落、status欠落、filed番号欠落、not_needed理由欠落は拒否、pendingは保存可能。
2. 複数rootのroundtrip、既存上書き・互換ID衝突・symlinkは拒否。
3. new-entry直後とPostToolUseでsystemMessage、todoでpending全件、file-issue下書きとfake起票で番号書戻し。
4. refs実在/canonical/immutability検査、pending→filedのみ更新可、supersedes導出view。
5. fake GitHubでOPENかつ閾値超過のfiledのみstaleへ列挙。
6. ADR/台帳/任意参照欄のChangePlan・VerificationDesignを同adapterで変換し、dsv2 queryでdeps/dependents/orphansを検証。永続envelopeも入力可能。
7. 全unit、asset_parity、maintainability_lintが成功し、baseline差分がない。
8. 全索引種別の不存在参照を発生元付きで検出し、不存在・repo外資産のnew-entryは保存しない。既存ファイル・ディレクトリは許可する。
9. cd・セミコロン・改行・rootの等号形式をBash/ctx_execute/ctx_batch_executeで通知する。
10. 同一ADRへの並行file-issueはIssueを1件だけ作成し、後続は最新のfiled状態を観測する。TCは test_adr_regressions.py / test_adr_concurrency.py。

# #452証跡

着手時のAC対象元は0件。99d89553（#538）でarchiveへ退役済み。詳細は adr/rationale.md。

## 実測

- 実装開始HEAD: `6e671db37d365156b3dbe61215a379434611fcea`。TD版1、プロンプト雛形版/基準content_hashは対象外（harness共有機構）。環境: Linux / Python3標準unittest。
- 全unit: `python3 -m unittest discover -s tests/unit`。2,133件、615.829秒、failures=4、skipped=9、exit 1。
- ログ: `issue_start/verify/logs/TD-adr-540-6e671db3-unit.txt`（stdout/stderrの実ダンプ）。
- 証跡の制約: 開始後、独立レビューの是正担当が同じworktreeで編集を開始した。従って本ログは6e671db3単独の厳密な証跡ではなく、開始HEADと実行期間を識別する記録である。是正後確定HEADの全unit/CI結果を別途確認する。
- ADR専用: 初回commit直後、`python3 -m unittest discover -s tests/unit -p test_adr.py` は8件/0.315秒、成功。
- `python3 -m maintainability_lint check`: exit 0、violations=0、accepted_debt=94。baseline差分なし。
- `python3 -m asset_parity check`: exit 0、MISSINGなし。既存のSTALE?診断あり。
- `python3 -m adr check --root issue_start/adr --require-base`: exit 0。

### 失敗の観測と処置

1. `test_codex_hook_trust.CodexHookTrustCliTests.test_mixed_trust_reports_untrusted_key_and_hash`: pre_tool_use:1:0を期待したが追加のpost_tool_use:0:0をfixtureが未信頼対象として取得。
2. `test_codex_hook_trust_hook.CodexHookTrustHookTests.test_untrusted_state_emits_only_a_warning`: 同じhook列末尾の想定が変化。
3. `test_issue_start_cli_assets.AssetParityTests.test_codex_hooks_register_only_scripts_that_exist`: Codex hook登録を存在する.sh入口で検査する契約に対し、python3 -m adr.hook直接登録では抽出scriptが0件。
4. `test_subagent_hooks.SettingsRegistrationTests.test_retired_merge_gate_registration_preserves_other_hooks`: Claude PostToolUse列の完全一致期待が、新規adr-notify登録を未包含。

原因: 新規PostToolUse追加に対する既存登録契約/fixtureの追従漏れ。親へ全件報告し、別コンテキストのfixerが処置する。本担当はコードを変更せず、失敗ログを保持した。

- 記録日時: 2026-10-16T04:45:30.986877+00:00
