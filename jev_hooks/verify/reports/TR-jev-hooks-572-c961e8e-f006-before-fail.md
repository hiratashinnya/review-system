---
id: TR-jev-hooks-572-c961e8e-f006-before-fail
version: 1
condition: failure
td_id: TD-jev-hooks-572-f006
result: FAIL
log_ref: jev_hooks/verify/logs/TD-jev-hooks-572-c961e8e-f006-fail.txt
---
# F-572-006 修正前失敗

2026-10-06、local c961e8eb3bb000f218f20cdee281795e98d8cd6fを孤立git archiveへ展開し、新しい恒久TC test_safety_sensitive_inputs.pyを実行した。SDK0.7.2/HTTP mock、fake canaryのみ。2testsの4subcase（Write/Edit × run_event/R4・semantic_eval/R4）がすべてFAIL。current_tool_input、skill_context.current_tool.input、設定selector/protected_operationsに不透明canary本文が残った。履歴tool_callsのみの省略が根因。

[恒久TC赤ログ](../logs/TD-jev-hooks-572-c961e8e-f006-fail.txt)。先行repro script/logも補助履歴として保存し、赤ログを緑結果へ書き換えない。修正後結果は[追加TR](TR-jev-hooks-572-c961e8e-f006-worktree.md)。

保存時にunittest出力行末の空白だけを除去した。失敗内容・件数は変更していない。
