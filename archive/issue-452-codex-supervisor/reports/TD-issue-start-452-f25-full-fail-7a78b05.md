---
id: TD-issue-start-452-f25
version: 1
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f25-full-fail-7a78b05.txt
---

# 目的

F-452-25のhost launch intentが、manifestのrole別handoff_templateとcanonical ledgerを照合した導出値を、inner role promptへ正しく配送することを検証する。

# 前提

- baselineはPR #518 merge commit 418425e以降のorigin/mainである。
- 正規Codex process/threadの起動・handoff・host publishを未修正成功証拠として扱わない。

# 手順・期待結果

1. implementer/fixerのrole別handoff pathとprompt配送を検証する。
2. 任意入力、legacy template、unknown placeholderをfail-closeする。
3. focused、asset parity、full unittest、coverageを実行する。

## 実測

- 実装commit: 7a78b05
- 通常full: 1872件中1870 PASS、2 failure、skip 13
- 失敗: 変更対象外のrate-limit parser 2件が期待値ではなく FALLBACK を返した。
- 根本原因: F-452-25差分外の既存rate-limit test/runtime条件不一致。
- 対処: 失敗を保持し、後続のcoverage実行結果と混同しない。
- ログ: tests/logs/TD-issue-start-452-f25-full-fail-7a78b05.txt
