---
id: TD-adr-540
version: 1
condition: normal
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
