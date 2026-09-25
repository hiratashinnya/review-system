---
id: TD-issue-start-452-f25
version: 2
condition: failure
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f25-r19-coverage-fail-c7eb009.txt
---

# 目的

F-452-25/26/27のcoverage検証で発生した環境依存失敗を保持し、後続の再計測PASSへ読み替えない。

# 実測

- 実装commit: `4229413`（rationale `c7eb009`）
- 1874件中1873 PASS、1 failure、skip 9
- 失敗: `test_real_outer_diagnosis_mount_denies_code_karte_and_git_writes`
- 根本原因: uvの一時Pythonが`/tmp`配下に置かれ、対象bwrapが意図的に`/tmp`をtmpfsへ置換するため、subprocessの実行ファイルが見えなかった。
- 対処: worktree配下cacheでcoverageを再実行し、1874件PASS（skip9）を確認した。
- 失敗ログは削除・上書きせず保持する。
