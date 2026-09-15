---
id: TD-issue-start-452-f25
version: 1
condition: normal
---

# 目的

F-452-25のhost launch intentが、manifestのrole別handoff_templateとcanonical ledgerを照合した導出値を、inner role promptへ正しく配送することを検証する。implementer/fixerの実運用入力を親AIやCLIの任意pathへ拡張しない。

# 前提

- baselineはPR #518 merge commit 418425e以降のorigin/mainである。
- implementerはissue_{issue}、fixerはissue_{issue}_fix_r{round}のrole別handoff pathを使う。
- host promptへ注入されるpathはroleごとにexact 1回であり、innerはそのpathだけへschema v1 handoffを書く。
- 正規Codex process/threadの起動・handoff・host publishを未修正成功証拠として扱わない。今回のunitはmodel-freeの事前検査である。

# 手順・期待結果

1. implementerとfixerのpure launch intentを生成する。各intentのhandoff_pathがcanonical ledgerと一致し、rendered prompt内の実pathがexact 1回であることを確認する。
2. handoff_pathをLaunchRequestへ追加しようとする入力が拒否されることを確認する。
3. manifestのlegacy handoff_templateまたはunknown handoff placeholderを注入し、MANIFEST_INVALIDでfail-closeすることを確認する。
4. focused unit、asset parity、full unittestを実行する。失敗時は原因を隠さずFAIL TRへ保存する。
5. uv経由coverageを実行し、htmlcov/index.html生成とcoverage summaryを記録する。coverageは全unitのPASS証拠とし、事前の通常full失敗は別FAIL TRとして保持する。

# TC

tests/unit/test_issue_start_gate.py::CodexLaunchIntentTests
tests/unit/test_codex_launch_control.py
tests/unit/test_codex_supervisor_shrink.py
tests/unit/test_issue_start_cli_assets.py

# 期待結果

- implementer/fixerともhost-derived role-specific handoff pathがpromptにexact 1回含まれる。
- 任意handoff path、legacy template、unknown placeholderはfail-closeする。
- focusedとasset parityはPASSする。
- coverage runは全unit PASS、skipのみ環境依存として報告される。
