---
id: TD-issue-start-452-f25
version: 1
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-f25-7a78b05.txt
---

# 目的

F-452-25のhost launch intentが、manifestのrole別handoff_templateとcanonical ledgerを照合した導出値を、inner role promptへ正しく配送することを検証する。

# 前提

- baselineはPR #518 merge commit 418425e以降のorigin/mainである。
- implementerはissue_{issue}、fixerはissue_{issue}_fix_r{round}のrole別handoff pathを使う。
- 正規Codex process/threadの起動・handoff・host publishを未修正成功証拠として扱わない。

# 手順・期待結果

1. implementerとfixerのpure launch intentを生成し、canonical ledgerと一致するhandoff pathがpromptにexact 1回含まれることを確認する。
2. LaunchRequest任意path、legacy template、unknown placeholderがfail-closeすることを確認する。
3. focused unit、asset parity、full unittest、coverageを実行する。

## 実測

- 実装commit: 7a78b05
- focused: 198件 PASS、skip 11
- asset parity: 39 assets checked、0 MISSING、13 staleness flags（informational）
- coverage full: 1872件 PASS、skip 9
- coverage: TOTAL 85%（9342 statements / 1405 missed）
- coverage HTML: htmlcov/index.html生成済み（未commit）
- path配送: implementer/fixer双方でrendered prompt内exact 1回
- fail-close: LaunchRequest任意path、legacy handoff template、unknown placeholder
- 既存の通常full FAIL 2件は別FAIL TRへ保持し、PASSへ読み替えていない。
