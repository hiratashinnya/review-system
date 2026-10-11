---
id: TD-issue-start-452-f25
version: 2
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-f25-r19-c7eb009.txt
---

# 目的

F-452-25/26/27のhost launch intentが、manifestのrole別handoff_templateとcanonical ledger/live Git factsを照合した導出値を、inner role promptへ正しく配送することを検証する。implementer/fixerの実運用入力を親AIやCLIの任意pathへ拡張せず、snapshot由来のpath・placeholder衝突をPopen前に止める。

# 前提

- baselineはPR #520のround19是正commit `4229413`（rationale追記 `c7eb009`）である。
- implementerはissue_{issue}、fixerはissue_{issue}_fix_r{round}のrole別handoff pathを使う。
- host promptへ注入されるhandoff_pathはroleごとにexact 1回であり、branch_name/repository/expected_oidもcanonical factsとして同じブロックへ配送し、innerはそのhandoff_pathだけへschema v1 handoffを書く。
- Issue/karte snapshotにcanonicalまたは別の`tmp/_handoff/` path、format placeholderがあればprompt組立前にfail-closeし、Popenへ到達しない。
- 正規Codex process/threadの起動・handoff・host publishを未修正成功証拠として扱わない。今回のunitはmodel-freeの事前検査である。

# 手順・期待結果

1. implementerとfixerのpure launch intentを生成する。各intentのhandoff_pathがcanonical ledgerと一致し、branch_name/repository/expected_oidを含むrendered prompt内の各実値が一意であることを確認する。
2. handoff_pathをLaunchRequestへ追加しようとする入力が拒否されることを確認する。
3. manifestのlegacy handoff_templateまたはunknown handoff placeholderを注入し、MANIFEST_INVALIDでfail-closeすることを確認する。
4. 両roleのIssue/karte snapshotへcanonical path再掲、別`tmp/_handoff/` path、format placeholder、role違いpathを注入し、prompt組立前のsource invalidで拒否されることを確認する。
5. focused unit、asset parity、full unittestを実行する。失敗時は原因を隠さずFAIL TRへ保存する。
6. uv経由coverageを実行し、htmlcov/index.html生成とcoverage summaryを記録する。coverageは全unitのPASS証拠とし、事前の通常full失敗は別FAIL TRとして保持する。

# TC

tests/unit/test_issue_start_gate.py::CodexLaunchIntentTests
tests/unit/test_issue_start_cli_assets.py::AssetParityTests
tests/unit/test_codex_launch_control.py
tests/unit/test_codex_supervisor.py
tests/unit/test_codex_supervisor_shrink.py

## 実測

- focused: 43件 PASS
- related: 244件 PASS、skip 13
- asset parity: 39 assets checked、0 MISSING、13 staleness flags（informational）
- regular full: 1874件 PASS、skip 9
- coverage full: 1874件 PASS、skip 9
- coverage: TOTAL 85%（9354 statements / 1406 missed）
- coverage HTML: htmlcov/index.html生成済み（未commit）
- canonical facts: implementer/fixer双方でhandoff_path、branch_name、repository、expected_oidをhost由来として配送
- prompt collision: canonical/別tmp/_handoff path、format placeholder、role違いpathをPopen前のsnapshot検証でfail-close
- 初回coverageのuv一時環境が`--tmpfs /tmp`へ隠れるFAILは別FAIL TRへ保存し、今回のPASSへ読み替えていない。
