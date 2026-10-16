---
id: TD-adr-540
version: 1
condition: normal
result: PASS
log_ref: issue_start/verify/logs/TD-adr-540-r2.txt
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
11. subshell・nested subshell・pipeline・backgroundのcdは親cwdへ漏れず、subshell内書込もそのrootを通知する。TCは test_adr_shell_scopes.py。
12. Codexの新PostToolUseは実在.sh入口を使い、おとりcwdに依存せず助言失敗時は継続する。trust検査はpre/post両hookの未信頼を検出し、Claude登録一覧は既存hookと新ADRを保持する。TCは test_adr_hook_entrypoints.py および既存hook検査。

# #452証跡

着手時のAC対象元は0件。99d89553（#538）でarchiveへ退役済み。詳細は adr/rationale.md。

## 実測（round 2 是正）

- Codex (AI) issue-fixer。TD版1 / 実装commit fbae967f / プロンプト雛形版 N/A / 基準content_hash N/A（ハーネス単体） / 実行日時 2026-10-16T04:49:53.117618+00:00 / Python標準unittest。
- コマンド: `python3 -m unittest tests.unit.test_adr tests.unit.test_adr_regressions tests.unit.test_adr_concurrency tests.unit.test_adr_shell_scopes tests.unit.test_adr_hook_entrypoints tests.unit.test_codex_hook_trust tests.unit.test_codex_hook_trust_hook tests.unit.test_issue_start_cli_assets tests.unit.test_subagent_hooks -v`。119件PASS。
- ログ: `issue_start/verify/logs/TD-adr-540-r2.txt`。以前の4failを含む既存hook検査とADR回帰を実行。subshell/nested subshell/pipeline/backgroundのcwd、全3tool経路、実script入口のdecoy import防止・fail-open、pre/post未信頼検出が成功。
- `python3 -m maintainability_lint check`: violations=0、accepted_debt=94。baseline変更なし。新規Python moduleは71行、49行、43行で100行以内。
- `python3 -m asset_parity check`: 42 assets、0 MISSING、既存staleness flag 19件。両監査のstdoutも同ログへ保存。
- round 2は全unitを重複実行せず、最新HEADのCIで全unit結果を確認する。
