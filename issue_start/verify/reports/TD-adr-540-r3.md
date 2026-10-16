---
id: TD-adr-540
version: 1
condition: normal
result: PASS
log_ref: issue_start/verify/logs/TD-adr-540-r3.txt
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
11. subshell・pipeline・backgroundを含むshellのcwdは実行後CLIが確定したrootを使用する。shell構文の模倣parserには依存しない。TCは test_adr_notice_results.py。
12. Codexの新PostToolUseは実在.sh入口を使い、おとりcwdに依存せず助言失敗時は継続する。trust検査はpre/post両hookの未信頼を検出し、Claude登録一覧は既存hookと新ADRを保持する。TCは test_adr_hook_entrypoints.py および既存hook検査。
13. 実bashのbrace/if/for/while/case/pushd/subshell/pipeline/background/quote/cd -を含むCLI書込後、3tool経路のPostToolUse実入口が書込rootのpendingをsystemMessageで返す。stdoutの全欠落・切詰め・部分receiptでも通知し、未登録rootを指す偽receiptは採用しない。TCは test_adr_notice_results.py。
14. thread/processのA/a・NFKC等価IDの同時書込は成功1件・拒否1件・保存1件でload可能。file-issueからwrite lockへの入れ子も既存並行起票TCで完了する。

# #452証跡

着手時のAC対象元は0件。99d89553（#538）でarchiveへ退役済み。詳細は adr/rationale.md。

## 実測（round 3 是正）

- Codex (AI) issue-fixer。TD版1 / 実装commit 287082e4（方式転換1df1e9bc、旧parser整理b956eb17） / プロンプト雛形版 N/A / 基準content_hash N/A / 実行日時 2026-10-16T05:00:30.397335+00:00 / Python標準unittest。
- コマンド: `python3 -m unittest tests.unit.test_adr tests.unit.test_adr_regressions tests.unit.test_adr_concurrency tests.unit.test_adr_hook_entrypoints tests.unit.test_adr_notice_results tests.unit.test_codex_hook_trust tests.unit.test_codex_hook_trust_hook tests.unit.test_issue_start_cli_assets tests.unit.test_subagent_hooks -v`。最終対象120件PASS（19.892s）。全unitの重複ローカル実行はせず最新CIで確認する。
- 実bashのbrace/if/for/while/case/pushd/subshell/pipeline/background/quote/cd -の11形を実行し、3toolと4種のresponse形（文字列・MCP content・切詰め・欠落）を実PostToolUse script入口へ渡した132経路で同一操作systemMessageを確認。書込先以外の未登録rootは通知に混ざらない。
- 偽receipt・部分receipt・破損した別登録rootでも正しいpendingを通知。未信頼tool_responseは読み順hintに限り、登録されたabsolute rootのTOMLを再読する。level-triggerのため登録済み別rootの未解決pendingも再通知する選択はadr/rationale.mdに記録。
- thread/processごとにA/aとNFKC等価IDの同時writeを実行し、成功1件・拒否1件・保存1件・load正常を確認。既存file-issue並行回帰もPASSし、file-issue→writeのlock取得順が完了する。
- maintainability_lint: violations=0 accepted_debt=94。baseline差分なし。新規Python moduleはnotice_roots.py 70行、test_adr_notice_results.py 78行で100行以内。asset_parity: 42 assets / 0 MISSING / 既存staleness19。
- F06の追加コード是正は行わず、既存4fail対象を含む回帰PASSのみ確認。最新PR対象SHAの全unit/build/lint CI完了は独立round4レビュー待ちであり、このTRで確認済みとはしない。
- 旧shell parserと専用TCは主文脈が削除し現行TDを実行結果E2Eへ統合。R2 TR/logは当時の実測履歴として保持。
