---
id: TR-jev-hooks-572-c961e8e-f006-worktree
version: 1
condition: failure
td_id: TD-jev-hooks-572-f006
result: PASS
log_ref: jev_hooks/verify/logs/TD-jev-hooks-572-c961e8e-f006-sdk-pass.txt
---
# F-572-006 修正後検証

2026-10-06、TD版1、Python3.12.14/Linux、SDK0.7.2/HTTP MockTransport。base local c961e8eb3bb000f218f20cdee281795e98d8cd6f、同tree公開head d648a02e8d2350a83d73218a7d6d7c91aafbb2c6に対する未commit差分を検証した。source snapshot SHA256 `e81cc6586e4efb50a5d729ba4bd78f0626207eb6855ec3b732f6a99da7301091` は[差分manifest](../logs/TD-jev-hooks-572-c961e8e-f006-source-snapshot.json)と親manifestから復元できる。verify文書/ログはdigest対象外としrecursive stampingを避ける。旧60/62件証跡は変更しない。

- 修正前: 旧版の孤立archiveに恒久TCを適用、2tests/4subcase失敗。[FAIL TR](TR-jev-hooks-572-c961e8e-f006-before-fail.md)と赤ログを保持。
- 修正後: SDK直接discover **69件PASS/skip0**。[ログ](../logs/TD-jev-hooks-572-c961e8e-f006-sdk-pass.txt)。Write/Editのrun_event/R4・semantic_eval/R4実HTTP body、設定selector/protected_operationsにも配置したcanaryの全除外を確認。通常file本文省略、shell全コピーの同一投影、引数/環境代入/heredoc省略、R3質問の.env言及保持を含む。実API通信なし。
- SDKなし: **69件PASS/skip4**（65件実行成功、任意SDK TCのみskip）。[ログ](../logs/TD-jev-hooks-572-c961e8e-f006-stdlib-pass.txt)。APIキー不要。
- maintainability: **violations0/accepted_debt134**、baseline変更なし。[ログ](../logs/TD-jev-hooks-572-c961e8e-f006-maintainability-pass.txt)。6Python moduleは57/69/26/82/80/55物理行、すべて100以内。
- time_fixture_lint: **16検出/violations0**。[ログ](../logs/TD-jev-hooks-572-c961e8e-f006-time-pass.txt)。既存canary22件証跡は前TRを保持。git diff --check成功。
- ローカル全unitは反復しない。以前の2105件11fail/1error、governance由来1件是正と旧HEAD同環境10fail/1errorは[前TR](TR-jev-hooks-572-b7ff3e5-worktree.md)の切分けを維持し、全unit成功とは扱わない。
- 修正前d648a02の[GitHub Actions run37474698960](https://github.com/hiratashinnya/review-system/actions/runs/37474698960)は全3 checks成功。F006修正後のCIと新独立レビューは公開後確認する。

入力projectionは履歴/current/R4 current_tool/selector/protected_operations全コピーで共通。引数値・機密path・コード本文・未解析shellの不足はunknownを増やすため、R4意味判定は限定される。投影後の実モデル精度/誤拒否率、未知秘密完全検出、通知実配送、WSL/Claude Code実セッションは未検証。設定schema不変、同PR是正につき質問/ルール版1.1を維持。settings結線・実API・mergeを実施していない。
