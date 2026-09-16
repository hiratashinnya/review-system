---
id: TD-issue-start-452-f25
version: 5
condition: normal
---

# 目的

F-452-25/26/27/28/29のhost launch intentが、manifestのrole別handoff_templateとcanonical ledger/live Git factsを照合した導出値を、inner role promptへ正しく配送することを検証する。implementer/fixerの実運用入力を親AIやCLIの任意pathへ拡張せず、snapshot由来の実handoff候補・reserved placeholder衝突だけをPopen前に止める。

# 前提

- baselineはPR #518 merge commit 418425e以降のorigin/mainである。
- implementerはissue_{issue}、fixerはissue_{issue}_fix_r{round}のrole別handoff pathを使う。
- host promptへ注入されるhandoff_pathはroleごとにexact 1回であり、branch_name/repository/expected_oidもcanonical factsとして同じブロックへ配送し、innerはそのhandoff_pathだけへschema v1 handoffを書く。
- Issue/karte snapshotにcanonical・別role・attackerの実handoff file candidate、またはhost authority/prompt reserved fieldのformat placeholderがあればprompt組立前にfail-closeし、Popenへ到達しない。候補は本文全体をshell実行・展開せず、一つのdeterministic lexerで先頭から末尾まで読み、HTML entity、componentごとのquote/backtick、POSIX/Windows separator、root側の重複・dot componentを正規化した後に判定する。途中quoted fragmentのseparatorはterminal状態にせず、候補全体の最終semantic path文字だけでfile/directory境界を決める。bareな`tmp/_handoff/`説明、reservedでない一般placeholder、通常コード断片は単一format passのreplacementとして許可する。
- 正規Codex process/threadの起動・handoff・host publishを未修正成功証拠として扱わない。今回のunitはmodel-freeの事前検査である。

# 手順・期待結果

1. implementerとfixerのpure launch intentを生成する。各intentのhandoff_pathがcanonical ledgerと一致し、branch_name/repository/expected_oidを含むrendered prompt内の各実値が一意であることを確認する。
2. handoff_pathをLaunchRequestへ追加しようとする入力が拒否されることを確認する。
3. manifestのlegacy handoff_templateまたはunknown handoff placeholderを注入し、MANIFEST_INVALIDでfail-closeすることを確認する。
4. 両roleのIssue/karte snapshotへcanonical path再掲、別`tmp/_handoff/` path、attacker path、dot/empty component、各component/filenameのquote・backtick・HTML entity、root/中間componentのquote内separator、POSIX/Windows separator、reserved placeholder、role違いpathを注入し、deterministic lexerの生成matrixでfile候補がprompt組立前のsource invalidとして拒否されることを確認する。bare directory mention、一般placeholder、通常コード断片は両roleで成功し、canonical pathはexact 1回だけ残ることを確認する。途中separator後にfilenameが続く候補は拒否し、候補全体が`tmp/_handoff/archive/`で終わるdirectory proseは許可する。
5. focused unit、asset parity、full unittestを実行する。失敗時は原因を隠さずFAIL TRへ保存する。
6. uv経由coverageを実行し、htmlcov/index.html生成とcoverage summaryを記録する。coverageは全unitのPASS証拠とし、事前の通常full失敗は別FAIL TRとして保持する。

# TC

tests/unit/test_issue_start_gate.py::CodexLaunchIntentTests
tests/unit/test_codex_launch_control.py
tests/unit/test_codex_supervisor_shrink.py
tests/unit/test_issue_start_cli_assets.py

# 期待結果

- implementer/fixerともhost-derived role-specific handoff pathがpromptにexact 1回含まれ、branch_name/repository/expected_oidもcanonical factsとして配送される。
- 任意handoff path、legacy template、host authority/prompt reserved placeholderはfail-closeする。pathのseparator・dot component・filename-only quote/backtickによる表記変形も同じ候補としてfail-closeする。
- snapshot由来の実handoff file candidateだけをPopen前にfail-closeし、bare directory mention・reservedでない一般placeholder・コード断片は許可する。
- focusedとasset parityはPASSする。
- coverage runは全unit PASS、skipのみ環境依存として報告される。
